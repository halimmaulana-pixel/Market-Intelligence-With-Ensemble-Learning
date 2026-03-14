"""
ml/evaluator.py — Evaluasi performa model SVR, SARIMA, dan Ensemble.

Fungsi utama:
  hitung_mae / rmse / mape / r2  — helper metrik individual
  evaluasi_semua_model()          — evaluasi SVR+SARIMA+Ensemble satu produk
  evaluasi_semua_produk()         — evaluasi semua produk yang sudah dilatih
"""
import os
import sys
import warnings
import joblib
import numpy as np

warnings.filterwarnings("ignore")

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TRAINED_MODELS_DIR
from database.models import Produk, ModelConfig, HistoriPenjualan
from ml.feature_engineering import buat_fitur_svr, transform_scaler, inverse_transform, load_scaler
from ml.ensemble import hitung_bobot


# ─── HELPER METRIK ────────────────────────────────────────────────────────────

def hitung_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(mean_absolute_error(y_true, y_pred))


def hitung_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def hitung_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Hitung MAPE, skip observasi dengan y_true = 0."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def hitung_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(r2_score(y_true, y_pred))


def _metrik_dict(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_pred = np.maximum(y_pred, 0)
    return {
        "mae":  hitung_mae(y_true, y_pred),
        "rmse": hitung_rmse(y_true, y_pred),
        "mape": hitung_mape(y_true, y_pred),
        "r2":   hitung_r2(y_true, y_pred),
    }


# ─── AMBIL DATA ───────────────────────────────────────────────────────────────

def _ambil_histori_df(produk_id: int, db: Session):
    """Ambil histori dari DB sebagai list of dict, sorted ascending."""
    rows = (
        db.query(HistoriPenjualan)
        .filter(HistoriPenjualan.produk_id == produk_id)
        .order_by(HistoriPenjualan.tanggal)
        .all()
    )
    import pandas as pd
    return pd.DataFrame([{
        "produk_id":    r.produk_id,
        "tanggal":      r.tanggal,
        "penjualan_rp": r.penjualan_rp,
        "cuaca":        r.cuaca or "cerah",
        "hari_besar":   r.hari_besar,
    } for r in rows])


# ─── EVALUASI SATU PRODUK ─────────────────────────────────────────────────────

def evaluasi_semua_model(produk_id: int, db: Session) -> dict:
    """
    Evaluasi SVR, SARIMA, dan Ensemble pada test set (20% terakhir data histori).

    Return dict:
      n_train, n_test,
      svr:      {mae, rmse, mape, r2},
      sarima:   {mae, rmse, mape, r2},
      ensemble: {mae, rmse, mape, r2, bobot_svr, bobot_sarima},
      kesimpulan: string Bahasa Indonesia
    """
    # ── Load data & split ─────────────────────────────────────────────────
    df = _ambil_histori_df(produk_id, db)
    if len(df) < 30:
        raise ValueError(f"Data histori produk ID {produk_id} terlalu sedikit untuk evaluasi.")

    df_fitur, kolom_fitur = buat_fitur_svr(df, produk_id)
    X = df_fitur[kolom_fitur].values
    y = df_fitur["penjualan_rp"].values

    y_univariat = np.array([r.penjualan_rp for r in
        db.query(HistoriPenjualan)
        .filter(HistoriPenjualan.produk_id == produk_id)
        .order_by(HistoriPenjualan.tanggal).all()], dtype=float)

    # SVR split (setelah feature engineering, 7 baris awal terpotong)
    split_svr  = int(len(X) * 0.8)
    X_test     = X[split_svr:]
    y_test_svr = y[split_svr:]

    # SARIMA split (series penuh)
    split_sarima  = int(len(y_univariat) * 0.8)
    y_train_sar   = y_univariat[:split_sarima]
    y_test_sarima = y_univariat[split_sarima:]

    # ── SVR prediksi test set ─────────────────────────────────────────────
    path_svr = os.path.join(TRAINED_MODELS_DIR, f"svr_{produk_id}.pkl")
    if not os.path.exists(path_svr):
        raise FileNotFoundError(f"Model SVR produk ID {produk_id} belum ada.")

    svr      = joblib.load(path_svr)
    scaler_X = load_scaler(produk_id)
    scaler_y = load_scaler(produk_id, suffix="_target")

    X_test_sc  = transform_scaler(X_test, scaler_X)
    y_svr_pred = inverse_transform(svr.predict(X_test_sc), scaler_y)
    y_svr_pred = np.maximum(y_svr_pred, 0)

    # SVR test set (actual) — dari feature engineering, sudah selaras dengan y_svr_pred
    y_test_svr_actual = y_test_svr  # 35 titik

    # ── SARIMA rolling forecast test set ──────────────────────────────────
    # Catatan alignment: FE membuang 7 baris pertama.
    # SVR test set = original rows [split_sarima+1 .. N-1] (35 titik)
    # SARIMA test set = original rows [split_sarima .. N-1] (36 titik)
    # SVR titik ke-0 = SARIMA titik ke-1 → skip 1 SARIMA forecast untuk alignment ensemble

    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()
    p  = config.sarima_p  if config else 1
    d  = config.sarima_d  if config else 1
    q  = config.sarima_q  if config else 1
    sp = config.sarima_sp if config else 1
    sd = config.sarima_sd if config else 1
    sq = config.sarima_sq if config else 1
    s  = config.sarima_s  if config else 7

    n_sarima_test = len(y_test_sarima)  # 36

    model_roll = SARIMAX(
        y_train_sar, order=(p, d, q),
        seasonal_order=(sp, sd, sq, s),
        enforce_stationarity=False, enforce_invertibility=False,
    ).fit(disp=False, maxiter=200)

    y_sarima_pred_full = []
    for i in range(n_sarima_test):
        fc = model_roll.forecast(steps=1)
        y_sarima_pred_full.append(float(fc[0]))
        model_roll = model_roll.append([y_test_sarima[i]], refit=False)
    y_sarima_pred_full = np.maximum(np.array(y_sarima_pred_full), 0)

    # SARIMA pada test set penuhnya (36 titik)
    y_sarima_pred = y_sarima_pred_full

    # Untuk ensemble: selaraskan ke 35 titik (skip SARIMA titik ke-0)
    n_test        = len(y_svr_pred)  # 35
    y_test_common = y_test_sarima[1:][:n_test]   # original rows 145-179
    y_svr_aligned    = y_svr_pred[:n_test]
    y_sarima_aligned = y_sarima_pred_full[1:][:n_test]

    # ── Ensemble ─────────────────────────────────────────────────────────
    try:
        bobot = hitung_bobot(produk_id, db)
    except ValueError:
        # Fallback 50-50 jika bobot belum ada
        bobot = {"bobot_svr": 0.5, "bobot_sarima": 0.5}

    w_svr    = bobot["bobot_svr"]
    w_sarima = bobot["bobot_sarima"]

    y_ens_pred = w_svr * y_svr_aligned + w_sarima * y_sarima_aligned

    # ── Hitung metrik ─────────────────────────────────────────────────────
    # SVR & Ensemble: 35 titik yang selaras
    # SARIMA: 36 titik test set penuhnya (lebih representatif)
    m_svr    = _metrik_dict(y_test_svr_actual, y_svr_aligned)
    m_sarima = _metrik_dict(y_test_sarima, y_sarima_pred)
    m_ens    = _metrik_dict(y_test_common, y_ens_pred)
    m_ens["bobot_svr"]    = w_svr
    m_ens["bobot_sarima"] = w_sarima

    # ── Kesimpulan otomatis ───────────────────────────────────────────────
    produk = db.query(Produk).filter(Produk.id == produk_id).first()
    nama   = produk.nama_produk if produk else f"Produk {produk_id}"
    mape_terbaik = min(m_svr["mape"], m_sarima["mape"], m_ens["mape"])

    if mape_terbaik == m_ens["mape"]:
        model_terbaik = "Ensemble"
        selisih_vs_svr    = m_svr["mape"]    - m_ens["mape"]
        selisih_vs_sarima = m_sarima["mape"] - m_ens["mape"]
        kesimpulan = (
            f"{nama}: Model Ensemble terbaik dengan MAPE {m_ens['mape']:.2f}%, "
            f"lebih baik {selisih_vs_svr:.2f}% dari SVR dan "
            f"{selisih_vs_sarima:.2f}% dari SARIMA."
        )
    elif mape_terbaik == m_svr["mape"]:
        model_terbaik = "SVR"
        kesimpulan = (
            f"{nama}: SVR terbaik dengan MAPE {m_svr['mape']:.2f}%, "
            f"ensemble MAPE {m_ens['mape']:.2f}% (selisih {m_ens['mape']-m_svr['mape']:.2f}%)."
        )
    else:
        model_terbaik = "SARIMA"
        kesimpulan = (
            f"{nama}: SARIMA terbaik dengan MAPE {m_sarima['mape']:.2f}%, "
            f"ensemble MAPE {m_ens['mape']:.2f}% (selisih {m_ens['mape']-m_sarima['mape']:.2f}%)."
        )

    return {
        "produk_id":    produk_id,
        "nama_produk":  nama,
        "n_train":      split_sarima,
        "n_test":       n_test,
        "svr":          m_svr,
        "sarima":       m_sarima,
        "ensemble":     m_ens,
        "model_terbaik": model_terbaik,
        "kesimpulan":   kesimpulan,
    }


# ─── EVALUASI SEMUA PRODUK ────────────────────────────────────────────────────

def evaluasi_semua_produk(db: Session) -> list:
    """
    Evaluasi semua produk aktif yang sudah dilatih (model_tersedia=True).
    Return list dict hasil evaluasi per produk.
    """
    configs = (
        db.query(ModelConfig)
        .filter(ModelConfig.model_tersedia == True)
        .all()
    )

    hasil = []
    for cfg in configs:
        try:
            ev = evaluasi_semua_model(cfg.produk_id, db)
            hasil.append(ev)
        except Exception as e:
            print(f"[EVALUATOR] WARNING produk_id={cfg.produk_id} — {e}")

    return hasil
