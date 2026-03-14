"""
ml/svr_model.py — Training dan prediksi model SVR per produk.

Fungsi utama:
  latih_svr()    — training SVR dengan GridSearchCV + TimeSeriesSplit
  prediksi_svr() — prediksi penjualan satu hari ke depan (Rp)
  evaluasi_svr() — hitung metrik MAE/RMSE/MAPE/R² pada test set
"""
import os
import sys
import time
import joblib
import numpy as np
import pandas as pd
from datetime import datetime

from sklearn.svm import SVR
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TRAINED_MODELS_DIR
from database.models import HistoriPenjualan, ModelConfig, Produk
from ml.feature_engineering import (
    buat_fitur_svr,
    fit_scaler,
    transform_scaler,
    inverse_transform,
    simpan_scaler,
    load_scaler,
    SEMUA_FITUR,
)

# Grid parameter SVR — kernel rbf wajib, tidak boleh diubah
PARAM_GRID = {
    "C":       [0.1, 1, 10, 100],
    "gamma":   [0.001, 0.01, 0.1, 1],
    "epsilon": [0.01, 0.1, 0.5],
}


def _path_svr(produk_id: int) -> str:
    os.makedirs(TRAINED_MODELS_DIR, exist_ok=True)
    return os.path.join(TRAINED_MODELS_DIR, f"svr_{produk_id}.pkl")


def _log(produk_id: int, pesan: str):
    print(f"[SVR] produk_id={produk_id} — {pesan}")


def _hitung_mape(y_aktual: np.ndarray, y_pred: np.ndarray) -> float:
    """Hitung MAPE, skip observasi dengan y_aktual = 0 (hindari division by zero)."""
    mask = y_aktual != 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_aktual[mask] - y_pred[mask]) / y_aktual[mask])) * 100)


def _ambil_data_histori(produk_id: int, db: Session) -> pd.DataFrame:
    """Ambil histori penjualan dari DB dan kembalikan sebagai DataFrame."""
    rows = (
        db.query(HistoriPenjualan)
        .filter(HistoriPenjualan.produk_id == produk_id)
        .order_by(HistoriPenjualan.tanggal)
        .all()
    )
    if not rows:
        raise ValueError(
            f"Tidak ada data histori untuk produk ID {produk_id}. "
            "Pastikan data sudah di-upload atau generate data dummy terlebih dahulu."
        )
    return pd.DataFrame([{
        "produk_id":    r.produk_id,
        "tanggal":      r.tanggal,
        "penjualan_rp": r.penjualan_rp,
        "cuaca":        r.cuaca or "cerah",
        "hari_besar":   r.hari_besar,
    } for r in rows])


# ─── TRAINING ─────────────────────────────────────────────────────────────────

def latih_svr(produk_id: int, db: Session, user_id: int | None = None) -> dict:
    """
    Latih model SVR untuk satu produk.

    Alur:
      1. Ambil histori dari DB
      2. Feature engineering
      3. Time-series split 80:20 (urutan temporal, TANPA shuffle)
      4. Cek auto_tune di model_config → GridSearchCV atau pakai param manual
      5. Simpan model ke .pkl
      6. Update model_config: mape_svr, last_trained, trained_by
      7. Return dict metrik + hyperparameter terbaik

    Args:
      produk_id — ID produk yang akan dilatih
      db        — SQLAlchemy Session
      user_id   — ID peneliti yang trigger training (untuk trained_by)
    """
    mulai = time.time()
    _log(produk_id, "Memulai training SVR...")

    # ── 1. Ambil data ──────────────────────────────────────────────────────
    df_histori = _ambil_data_histori(produk_id, db)
    _log(produk_id, f"Data diambil: {len(df_histori)} baris")

    if len(df_histori) < 30:
        raise ValueError(
            f"Data histori produk ID {produk_id} hanya {len(df_histori)} baris. "
            "Minimal 30 baris diperlukan untuk melatih model SVR."
        )

    # ── 2. Feature engineering ─────────────────────────────────────────────
    df_fitur, kolom_fitur = buat_fitur_svr(df_histori, produk_id)
    _log(produk_id, f"Fitur dibuat: {len(df_fitur)} baris × {len(kolom_fitur)} fitur")

    X = df_fitur[kolom_fitur].values
    y = df_fitur["penjualan_rp"].values

    # ── 3. Time-series split 80:20 — WAJIB pertahankan urutan temporal ──────
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    _log(produk_id, f"Split — train: {len(X_train)} baris, test: {len(X_test)} baris")

    # ── 4. Scaling ─────────────────────────────────────────────────────────
    scaler_X = fit_scaler(X_train)
    scaler_y = fit_scaler(y_train.reshape(-1, 1))

    X_train_sc = transform_scaler(X_train, scaler_X)
    y_train_sc = transform_scaler(y_train.reshape(-1, 1), scaler_y).ravel()
    X_test_sc  = transform_scaler(X_test, scaler_X)

    simpan_scaler(scaler_X, produk_id)
    simpan_scaler(scaler_y, produk_id, suffix="_target")
    _log(produk_id, "Scaler disimpan.")

    # ── 5. Cek auto_tune dari model_config ────────────────────────────────
    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()

    if config and not config.auto_tune:
        # Gunakan parameter manual dari DB
        best_params = {
            "C":       config.svr_C,
            "gamma":   config.svr_gamma,
            "epsilon": config.svr_epsilon,
        }
        svr = SVR(kernel="rbf", **best_params)
        svr.fit(X_train_sc, y_train_sc)
        _log(produk_id, f"auto_tune=False → param manual: {best_params}")
    else:
        # GridSearchCV + TimeSeriesSplit (auto_tune=True)
        tscv = TimeSeriesSplit(n_splits=5)
        grid = GridSearchCV(
            SVR(kernel="rbf"),
            PARAM_GRID,
            cv=tscv,
            scoring="neg_mean_absolute_error",
            n_jobs=-1,
            refit=True,
            verbose=0,
        )
        grid.fit(X_train_sc, y_train_sc)
        svr = grid.best_estimator_
        best_params = grid.best_params_
        _log(produk_id, f"auto_tune=True → GridSearch selesai, best: {best_params}")

    # ── 6. Evaluasi pada test set ─────────────────────────────────────────
    y_pred_sc = svr.predict(X_test_sc)
    y_pred    = inverse_transform(y_pred_sc, scaler_y)
    y_pred    = np.maximum(y_pred, 0)  # prediksi tidak boleh negatif

    mae  = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    mape = _hitung_mape(y_test, y_pred)
    r2   = float(r2_score(y_test, y_pred))
    durasi = time.time() - mulai

    _log(produk_id, f"Metrik test — MAE: {mae:,.0f} | RMSE: {rmse:,.0f} | MAPE: {mape:.2f}% | R²: {r2:.4f}")
    _log(produk_id, f"Durasi training: {durasi:.1f} detik")

    # ── 7. Simpan model .pkl ──────────────────────────────────────────────
    joblib.dump(svr, _path_svr(produk_id))
    _log(produk_id, f"Model disimpan ke: svr_{produk_id}.pkl")

    # ── 8. Update model_config di DB ─────────────────────────────────────
    if config:
        config.mape_svr       = mape
        config.svr_C          = float(best_params["C"])
        config.svr_gamma      = float(best_params["gamma"])
        config.svr_epsilon    = float(best_params["epsilon"])
        config.last_trained   = datetime.utcnow()
        config.model_tersedia = True
        if user_id:
            config.trained_by = user_id
        db.commit()
        _log(produk_id, "model_config diperbarui di DB.")

    return {
        "mae":              mae,
        "rmse":             rmse,
        "mape":             mape,
        "r2":               r2,
        "n_train":          len(X_train),
        "n_test":           len(X_test),
        "hyperparameter":   best_params,
        "durasi_detik":     durasi,
    }


# ─── PREDIKSI ─────────────────────────────────────────────────────────────────

def prediksi_svr(produk_id: int, fitur_input: dict, db: Session) -> float:
    """
    Prediksi penjualan satu hari ke depan untuk satu produk.

    Args:
      produk_id   — ID produk
      fitur_input — dict dengan key sesuai SEMUA_FITUR
                    (bisa dihasilkan oleh buat_fitur_svr() untuk baris terakhir)
      db          — SQLAlchemy Session

    Return:
      Nilai prediksi dalam Rupiah (float)
    """
    # Load model dan scaler
    path_svr = _path_svr(produk_id)
    if not os.path.exists(path_svr):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Model SVR belum dilatih untuk produk ID {produk_id}. Hubungi Peneliti.",
        )

    svr      = joblib.load(path_svr)
    scaler_X = load_scaler(produk_id)
    scaler_y = load_scaler(produk_id, suffix="_target")

    # Susun vektor fitur sesuai urutan SEMUA_FITUR
    X_raw = np.array([[fitur_input[f] for f in SEMUA_FITUR]], dtype=float)
    X_sc  = transform_scaler(X_raw, scaler_X)

    y_sc  = svr.predict(X_sc)
    y_rp  = inverse_transform(y_sc, scaler_y)

    return float(max(y_rp[0], 0))  # tidak boleh negatif


# ─── EVALUASI ─────────────────────────────────────────────────────────────────

def evaluasi_svr(produk_id: int, db: Session) -> dict:
    """
    Hitung ulang metrik evaluasi SVR pada test set (20% terakhir data histori).

    Return:
      dict berisi mae, rmse, mape, r2, n_test, hyperparameter
    """
    _log(produk_id, "Menghitung metrik evaluasi...")

    df_histori = _ambil_data_histori(produk_id, db)
    df_fitur, kolom_fitur = buat_fitur_svr(df_histori, produk_id)

    X = df_fitur[kolom_fitur].values
    y = df_fitur["penjualan_rp"].values

    split_idx = int(len(X) * 0.8)
    X_test = X[split_idx:]
    y_test = y[split_idx:]

    path_svr = _path_svr(produk_id)
    if not os.path.exists(path_svr):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Model SVR belum dilatih untuk produk ID {produk_id}. Hubungi Peneliti.",
        )

    svr      = joblib.load(path_svr)
    scaler_X = load_scaler(produk_id)
    scaler_y = load_scaler(produk_id, suffix="_target")

    X_test_sc = transform_scaler(X_test, scaler_X)
    y_pred_sc = svr.predict(X_test_sc)
    y_pred    = inverse_transform(y_pred_sc, scaler_y)
    y_pred    = np.maximum(y_pred, 0)

    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()

    return {
        "mae":  float(mean_absolute_error(y_test, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "mape": _hitung_mape(y_test, y_pred),
        "r2":   float(r2_score(y_test, y_pred)),
        "n_test": len(y_test),
        "hyperparameter": {
            "C":       config.svr_C       if config else None,
            "gamma":   config.svr_gamma   if config else None,
            "epsilon": config.svr_epsilon if config else None,
        },
    }
