"""
ml/sarima_model.py — Training dan prediksi model SARIMA per produk.

Fungsi utama:
  latih_sarima()    — training SARIMA dengan auto_arima atau orde manual
  prediksi_sarima() — forecast h langkah ke depan (Rp)
  evaluasi_sarima() — hitung metrik + diagnostik Ljung-Box
"""
import os
import sys
import time
import joblib
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

# Redam semua warning statsmodels / pmdarima agar terminal tidak berisik
warnings.filterwarnings("ignore")

from statsmodels.tsa.stattools import adfuller
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX
import pmdarima as pm
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TRAINED_MODELS_DIR
from database.models import HistoriPenjualan, ModelConfig


def _path_sarima(produk_id: int) -> str:
    os.makedirs(TRAINED_MODELS_DIR, exist_ok=True)
    return os.path.join(TRAINED_MODELS_DIR, f"sarima_{produk_id}.pkl")


def _log(produk_id: int, pesan: str):
    print(f"[SARIMA] produk_id={produk_id} — {pesan}")


def _hitung_mape(y_aktual: np.ndarray, y_pred: np.ndarray) -> float:
    """Hitung MAPE, skip observasi dengan y_aktual = 0."""
    mask = y_aktual != 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_aktual[mask] - y_pred[mask]) / y_aktual[mask])) * 100)


def _ambil_series(produk_id: int, db: Session) -> np.ndarray:
    """Ambil series univariat penjualan_rp dari DB, sort ascending by tanggal."""
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
    return np.array([r.penjualan_rp for r in rows], dtype=float)


def _uji_adf(series: np.ndarray, produk_id: int) -> int:
    """
    Uji stasioneritas dengan ADF test.
    Jika p-value > 0.05 → tidak stasioner → sarankan d=1.
    Return nilai d yang disarankan (0 atau 1).
    """
    hasil_adf = adfuller(series, autolag="AIC")
    p_value = hasil_adf[1]
    _log(produk_id, f"ADF test — p-value: {p_value:.4f} ({'stasioner' if p_value <= 0.05 else 'tidak stasioner, d=1 disarankan'})")
    return 0 if p_value <= 0.05 else 1


def _ljung_box(residual: np.ndarray, produk_id: int) -> float:
    """
    Uji Ljung-Box pada residual model.
    Catat hasilnya — jangan gagalkan training jika tidak lolos.
    Return p-value lag=10.
    """
    try:
        lb_hasil = acorr_ljungbox(residual, lags=[10], return_df=True)
        pval = float(lb_hasil["lb_pvalue"].iloc[0])
        status = "baik (tidak ada autokorelasi residual)" if pval > 0.05 else "ada autokorelasi residual — catat sebagai warning"
        _log(produk_id, f"Ljung-Box lag=10 — p-value: {pval:.4f} ({status})")
        return pval
    except Exception:
        _log(produk_id, "Ljung-Box test tidak dapat dijalankan — dilewati.")
        return float("nan")


# ─── TRAINING ─────────────────────────────────────────────────────────────────

def latih_sarima(produk_id: int, db: Session, user_id: int | None = None) -> dict:
    """
    Latih model SARIMA untuk satu produk.

    Alur:
      1. Ambil series univariat dari DB
      2. ADF test → tentukan d
      3. Cek auto_tune di model_config → auto_arima atau orde manual
      4. Split 80:20 temporal, latih pada train set
      5. Ljung-Box test pada residual (catat, tidak memblokir)
      6. Evaluasi pada test set
      7. Simpan model ke .pkl
      8. Update model_config di DB

    Return: dict metrik + orde model
    """
    mulai = time.time()
    _log(produk_id, "Memulai training SARIMA...")

    # ── 1. Ambil data ──────────────────────────────────────────────────────
    y = _ambil_series(produk_id, db)
    _log(produk_id, f"Data diambil: {len(y)} observasi")

    if len(y) < 30:
        raise ValueError(
            f"Data histori produk ID {produk_id} hanya {len(y)} baris. "
            "Minimal 30 baris diperlukan untuk melatih model SARIMA."
        )

    # ── 2. Split 80:20 time-series — urutan temporal wajib terjaga ─────────
    split_idx = int(len(y) * 0.8)
    y_train = y[:split_idx]
    y_test  = y[split_idx:]
    _log(produk_id, f"Split — train: {len(y_train)} obs, test: {len(y_test)} obs")

    # ── 3. Cek auto_tune dari model_config ────────────────────────────────
    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()
    auto_tune = config.auto_tune if config else True

    if auto_tune:
        # ── ADF test sebelum auto_arima ────────────────────────────────────
        d_adf = _uji_adf(y_train, produk_id)

        _log(produk_id, "auto_tune=True → menjalankan auto_arima (ini bisa memakan waktu)...")
        model_aa = pm.auto_arima(
            y_train,
            seasonal=True,
            m=7,
            d=d_adf if d_adf == 1 else None,  # paksa d jika tidak stasioner
            information_criterion="aic",
            stepwise=True,
            max_p=3, max_q=3,
            max_P=2, max_Q=2,
            suppress_warnings=True,
            error_action="ignore",
            trace=False,
        )
        orde = model_aa.order          # (p, d, q)
        orde_s = model_aa.seasonal_order  # (P, D, Q, s)
        p, d, q = orde
        sp, sd, sq, s = orde_s
        _log(produk_id, f"auto_arima selesai → orde: ({p},{d},{q})({sp},{sd},{sq}){s}")

    else:
        # Pakai orde manual dari DB
        p  = config.sarima_p
        d  = config.sarima_d
        q  = config.sarima_q
        sp = config.sarima_sp
        sd = config.sarima_sd
        sq = config.sarima_sq
        s  = config.sarima_s
        _log(produk_id, f"auto_tune=False → orde manual: ({p},{d},{q})({sp},{sd},{sq}){s}")

    # ── 4. Latih SARIMAX pada train set ───────────────────────────────────
    model_sarima = SARIMAX(
        y_train,
        order=(p, d, q),
        seasonal_order=(sp, sd, sq, s),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    hasil_fit = model_sarima.fit(disp=False, maxiter=200)

    # ── 5. Ljung-Box pada residual ────────────────────────────────────────
    lb_pvalue = _ljung_box(hasil_fit.resid, produk_id)

    # ── 6. Evaluasi pada test set — forecast step-by-step ─────────────────
    # Re-fit model pada seluruh train untuk prediksi
    y_pred = []
    # Gunakan append (online update) agar tidak mahal
    model_rolling = SARIMAX(
        y_train,
        order=(p, d, q),
        seasonal_order=(sp, sd, sq, s),
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False, maxiter=200)

    for i in range(len(y_test)):
        fc = model_rolling.forecast(steps=1)
        y_pred.append(float(fc[0]))
        # Update model dengan observasi aktual
        model_rolling = model_rolling.append([y_test[i]], refit=False)

    y_pred_arr = np.maximum(np.array(y_pred), 0)  # tidak boleh negatif

    mae  = float(mean_absolute_error(y_test, y_pred_arr))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred_arr)))
    mape = _hitung_mape(y_test, y_pred_arr)
    r2   = float(r2_score(y_test, y_pred_arr))
    durasi = time.time() - mulai

    _log(produk_id, f"Metrik test — MAE: {mae:,.0f} | RMSE: {rmse:,.0f} | MAPE: {mape:.2f}% | R²: {r2:.4f}")
    _log(produk_id, f"Durasi training: {durasi:.1f} detik")

    # ── 7. Simpan model final (fit pada SEMUA data) ──────────────────────
    model_final = SARIMAX(
        y,
        order=(p, d, q),
        seasonal_order=(sp, sd, sq, s),
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False, maxiter=200)

    joblib.dump(model_final, _path_sarima(produk_id))
    _log(produk_id, f"Model disimpan ke: sarima_{produk_id}.pkl")

    # ── 8. Update model_config di DB ─────────────────────────────────────
    if config:
        config.sarima_p      = int(p)
        config.sarima_d      = int(d)
        config.sarima_q      = int(q)
        config.sarima_sp     = int(sp)
        config.sarima_sd     = int(sd)
        config.sarima_sq     = int(sq)
        config.sarima_s      = int(s)
        config.mape_sarima   = mape
        config.last_trained  = datetime.utcnow()
        config.model_tersedia = True
        if user_id:
            config.trained_by = user_id
        db.commit()
        _log(produk_id, "model_config diperbarui di DB.")

    return {
        "mae":           mae,
        "rmse":          rmse,
        "mape":          mape,
        "r2":            r2,
        "n_train":       len(y_train),
        "n_test":        len(y_test),
        "orde":          {"p": p, "d": d, "q": q},
        "orde_seasonal": {"sp": sp, "sd": sd, "sq": sq, "s": s},
        "lb_pvalue":     lb_pvalue,
        "durasi_detik":  durasi,
    }


# ─── PREDIKSI ─────────────────────────────────────────────────────────────────

def prediksi_sarima(produk_id: int, db: Session, steps: int = 1) -> float:
    """
    Forecast h langkah ke depan menggunakan model SARIMA yang sudah dilatih.

    Args:
      produk_id — ID produk
      db        — SQLAlchemy Session
      steps     — jumlah langkah ke depan (default=1 untuk prediksi esok hari)

    Return:
      Nilai forecast pada langkah ke-steps dalam Rupiah (float)
    """
    path = _path_sarima(produk_id)
    if not os.path.exists(path):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Model SARIMA belum dilatih untuk produk ID {produk_id}. Hubungi Peneliti.",
        )

    model_fit = joblib.load(path)
    forecast = model_fit.forecast(steps=steps)
    nilai = float(forecast.iloc[steps - 1]) if hasattr(forecast, "iloc") else float(forecast[steps - 1])
    return max(nilai, 0.0)  # tidak boleh negatif


# ─── EVALUASI ─────────────────────────────────────────────────────────────────

def evaluasi_sarima(produk_id: int, db: Session) -> dict:
    """
    Hitung metrik evaluasi SARIMA pada test set (20% terakhir data histori).

    Return:
      dict berisi mae, rmse, mape, r2, orde_model, ljung_box_pvalue
    """
    _log(produk_id, "Menghitung metrik evaluasi...")

    y = _ambil_series(produk_id, db)
    split_idx = int(len(y) * 0.8)
    y_train = y[:split_idx]
    y_test  = y[split_idx:]

    path = _path_sarima(produk_id)
    if not os.path.exists(path):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail=f"Model SARIMA belum dilatih untuk produk ID {produk_id}. Hubungi Peneliti.",
        )

    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()
    p  = config.sarima_p  if config else 1
    d  = config.sarima_d  if config else 1
    q  = config.sarima_q  if config else 1
    sp = config.sarima_sp if config else 1
    sd = config.sarima_sd if config else 1
    sq = config.sarima_sq if config else 1
    s  = config.sarima_s  if config else 7

    # Re-run rolling forecast pada test set
    model_rolling = SARIMAX(
        y_train,
        order=(p, d, q),
        seasonal_order=(sp, sd, sq, s),
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False, maxiter=200)

    y_pred = []
    for i in range(len(y_test)):
        fc = model_rolling.forecast(steps=1)
        y_pred.append(float(fc[0]))
        model_rolling = model_rolling.append([y_test[i]], refit=False)

    y_pred_arr = np.maximum(np.array(y_pred), 0)
    lb_pvalue = _ljung_box(joblib.load(path).resid, produk_id)

    return {
        "mae":            float(mean_absolute_error(y_test, y_pred_arr)),
        "rmse":           float(np.sqrt(mean_squared_error(y_test, y_pred_arr))),
        "mape":           _hitung_mape(y_test, y_pred_arr),
        "r2":             float(r2_score(y_test, y_pred_arr)),
        "n_test":         len(y_test),
        "orde_model":     f"({p},{d},{q})({sp},{sd},{sq}){s}",
        "ljung_box_pvalue": lb_pvalue,
    }
