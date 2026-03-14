"""
ml/verbose.py — Transparansi proses prediksi per produk untuk endpoint verbose.

Fungsi utama:
  buat_proses_detail() — susun dict lengkap 5 tahap proses ML untuk satu produk.
"""
import os
import sys
import time
import joblib
import warnings
import numpy as np
from datetime import date

warnings.filterwarnings("ignore")

from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TRAINED_MODELS_DIR
from database.models import Produk, ModelConfig, HistoriPenjualan
from ml.feature_engineering import buat_fitur_svr, load_scaler, SEMUA_FITUR
from ml.ensemble import _buat_fitur_prediksi, hitung_bobot

import pandas as pd


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _path_svr(produk_id: int) -> str:
    return os.path.join(TRAINED_MODELS_DIR, f"svr_{produk_id}.pkl")


def _path_sarima(produk_id: int) -> str:
    return os.path.join(TRAINED_MODELS_DIR, f"sarima_{produk_id}.pkl")


def _ambil_data_histori_df(produk_id: int, db: Session) -> pd.DataFrame:
    """Ambil histori penjualan dari DB sebagai DataFrame."""
    rows = (
        db.query(HistoriPenjualan)
        .filter(HistoriPenjualan.produk_id == produk_id)
        .order_by(HistoriPenjualan.tanggal)
        .all()
    )
    if not rows:
        raise ValueError(f"Tidak ada data histori untuk produk ID {produk_id}.")
    return pd.DataFrame([{
        "produk_id":    r.produk_id,
        "tanggal":      r.tanggal,
        "penjualan_rp": r.penjualan_rp,
        "cuaca":        r.cuaca or "cerah",
        "hari_besar":   r.hari_besar,
    } for r in rows])


def _safe_tolist(arr) -> list:
    """Konversi numpy array / scalar ke list Python biasa."""
    try:
        if hasattr(arr, "tolist"):
            return arr.tolist()
        return list(arr)
    except Exception:
        return []


# ─── TAHAP 1: FEATURE ENGINEERING ────────────────────────────────────────────

def _tahap_1_fitur(
    produk_id: int,
    tanggal: date,
    cuaca: str,
    hari_besar: str | None,
    db: Session,
) -> tuple[dict, pd.DataFrame, list[str], np.ndarray, object, object]:
    """
    Transparansi feature engineering.

    Return:
      (tahap_dict, df_fitur, kolom_fitur, X_scaled, scaler_x, scaler_y)
    """
    df_histori = _ambil_data_histori_df(produk_id, db)
    df_fitur, kolom_fitur = buat_fitur_svr(df_histori, produk_id)

    scaler_x = load_scaler(produk_id, "")
    scaler_y = load_scaler(produk_id, "_target")

    fitur_dict = _buat_fitur_prediksi(produk_id, tanggal, cuaca, hari_besar, db)
    X_raw = np.array([[fitur_dict.get(k, 0) for k in kolom_fitur]], dtype=float)
    X_scaled = scaler_x.transform(X_raw)

    # Contoh scaling dari baris terakhir df_fitur
    contoh_sebelum = X_raw[0].tolist()
    contoh_sesudah = X_scaled[0].tolist()

    x_min = _safe_tolist(scaler_x.data_min_)
    x_max = _safe_tolist(scaler_x.data_max_)

    tahap = {
        "n_observasi": int(len(df_fitur)),
        "n_fitur": int(len(kolom_fitur)),
        "nama_fitur": kolom_fitur,
        "contoh_sebelum_scaling": contoh_sebelum,
        "contoh_sesudah_scaling": contoh_sesudah,
        "x_min": x_min,
        "x_max": x_max,
    }
    return tahap, df_fitur, kolom_fitur, X_scaled, scaler_x, scaler_y


# ─── TAHAP 2: SVR ─────────────────────────────────────────────────────────────

def _tahap_2_svr(
    produk_id: int,
    df_fitur: pd.DataFrame,
    kolom_fitur: list[str],
    X_scaled: np.ndarray,
    scaler_x,
    scaler_y,
    db: Session,
) -> tuple[dict, float]:
    """
    Transparansi model SVR.

    Return:
      (tahap_dict, prediksi_rp_svr)
    """
    t0 = time.time()
    path_svr = _path_svr(produk_id)

    svr_model = joblib.load(path_svr)
    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()

    # Hyperparameter
    kernel = "rbf"
    svr_C = config.svr_C if config else None
    svr_gamma = config.svr_gamma if config else None
    svr_epsilon = config.svr_epsilon if config else 0.1

    # Support vectors
    try:
        n_sv = int(svr_model.support_vectors_.shape[0])
    except Exception:
        n_sv = 0

    # Training samples
    try:
        n_training = int(svr_model.support_vectors_.shape[1]) if hasattr(svr_model, "support_vectors_") else 0
        # Perkiraan dari df_fitur
        n_training = int(len(df_fitur) * 0.8)
    except Exception:
        n_training = 0

    # Prediksi
    prediksi_scaled_svr = float(svr_model.predict(X_scaled)[0])

    y_min = float(scaler_y.data_min_[0])
    y_max = float(scaler_y.data_max_[0])
    prediksi_rp_svr = prediksi_scaled_svr * (y_max - y_min) + y_min
    prediksi_rp_svr = max(prediksi_rp_svr, 0.0)

    # Epsilon tube visualization: last 35 baris df_fitur sebagai test set
    epsilon_tube_data = []
    try:
        n_test = min(35, len(df_fitur))
        X_test = df_fitur[kolom_fitur].values[-n_test:]
        y_test = df_fitur["penjualan_rp"].values[-n_test:]
        X_test_scaled = scaler_x.transform(X_test)
        y_pred_test_scaled = svr_model.predict(X_test_scaled)
        y_pred_test = y_pred_test_scaled * (y_max - y_min) + y_min
        epsilon_rp = svr_epsilon * (y_max - y_min)

        for i in range(n_test):
            err = abs(float(y_test[i]) - float(y_pred_test[i]))
            epsilon_tube_data.append({
                "x": int(i),
                "y_actual": round(float(y_test[i]), 2),
                "y_pred": round(float(y_pred_test[i]), 2),
                "error": round(err, 2),
                "in_tube": bool(err <= epsilon_rp),
            })
    except Exception:
        epsilon_rp = 0.0

    durasi_ms = round((time.time() - t0) * 1000, 2)

    tahap = {
        "file_model": f"svr_{produk_id}.pkl",
        "kernel": kernel,
        "C": svr_C,
        "gamma": svr_gamma,
        "epsilon": svr_epsilon,
        "n_support_vectors": n_sv,
        "n_training_samples": n_training,
        "prediksi_scaled": round(prediksi_scaled_svr, 6),
        "prediksi_rp": round(prediksi_rp_svr, 2),
        "durasi_ms": durasi_ms,
        "y_min": round(y_min, 2),
        "y_max": round(y_max, 2),
        "epsilon_tube": {
            "epsilon_rp": round(epsilon_rp, 2),
            "data_test": epsilon_tube_data,
        },
    }
    return tahap, prediksi_rp_svr


# ─── TAHAP 3: SARIMA ──────────────────────────────────────────────────────────

def _tahap_3_sarima(
    produk_id: int,
    db: Session,
) -> tuple[dict, float]:
    """
    Transparansi model SARIMA.

    Return:
      (tahap_dict, prediksi_rp_sarima)
    """
    t0 = time.time()
    path_sarima = _path_sarima(produk_id)
    sarima_model = joblib.load(path_sarima)

    # Ambil series dari DB
    rows = (
        db.query(HistoriPenjualan)
        .filter(HistoriPenjualan.produk_id == produk_id)
        .order_by(HistoriPenjualan.tanggal)
        .all()
    )
    series = np.array([r.penjualan_rp for r in rows], dtype=float)

    # ADF test
    adf_pvalue = float("nan")
    adf_stasioner = None
    try:
        from statsmodels.tsa.stattools import adfuller
        adf_result = adfuller(series, autolag="AIC")
        adf_pvalue = float(adf_result[1])
        adf_stasioner = bool(adf_pvalue <= 0.05)
    except Exception:
        pass

    # Orde model dari ModelConfig
    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()
    p  = config.sarima_p  if config else 1
    d  = config.sarima_d  if config else 1
    q  = config.sarima_q  if config else 1
    sp = config.sarima_sp if config else 1
    sd = config.sarima_sd if config else 1
    sq = config.sarima_sq if config else 1
    s  = config.sarima_s  if config else 7

    orde_str = f"({p},{d},{q})({sp},{sd},{sq})[{s}]"

    # Koefisien AR / MA
    koefisien_ar = []
    koefisien_ma = []
    koefisien_seasonal_ar = []
    koefisien_seasonal_ma = []
    try:
        koefisien_ar = _safe_tolist(sarima_model.arparams())
    except Exception:
        pass
    try:
        koefisien_ma = _safe_tolist(sarima_model.maparams())
    except Exception:
        pass
    try:
        # Statsmodels SARIMAX result object
        params = sarima_model.params
        param_names = sarima_model.param_names if hasattr(sarima_model, "param_names") else []
        ar_names  = [n for n in param_names if n.startswith("ar.") and not n.startswith("ar.S")]
        ma_names  = [n for n in param_names if n.startswith("ma.") and not n.startswith("ma.S")]
        sar_names = [n for n in param_names if n.startswith("ar.S")]
        sma_names = [n for n in param_names if n.startswith("ma.S")]
        if ar_names:
            koefisien_ar = [round(float(params[n]), 6) for n in ar_names]
        if ma_names:
            koefisien_ma = [round(float(params[n]), 6) for n in ma_names]
        if sar_names:
            koefisien_seasonal_ar = [round(float(params[n]), 6) for n in sar_names]
        if sma_names:
            koefisien_seasonal_ma = [round(float(params[n]), 6) for n in sma_names]
    except Exception:
        pass

    # Residual
    resid = np.array([])
    try:
        resid = np.array(sarima_model.resid, dtype=float)
        resid = resid[~np.isnan(resid)]
    except Exception:
        pass

    # Ljung-Box
    lb_pvalue = float("nan")
    try:
        from statsmodels.stats.diagnostic import acorr_ljungbox
        if len(resid) > 15:
            lb = acorr_ljungbox(resid, lags=[10], return_df=True)
            lb_pvalue = float(lb["lb_pvalue"].iloc[-1])
    except Exception:
        pass

    # ACF / PACF
    acf_values = []
    pacf_values = []
    acf_lags = []
    try:
        from statsmodels.tsa.stattools import acf, pacf
        if len(resid) > 20:
            n_lags = min(20, len(resid) // 2 - 1)
            acf_vals = acf(resid, nlags=n_lags)
            acf_values = [round(float(v), 6) for v in acf_vals.tolist()]
            acf_lags = list(range(len(acf_values)))
            try:
                pacf_vals = pacf(resid, nlags=n_lags)
                pacf_values = [round(float(v), 6) for v in pacf_vals.tolist()]
            except Exception:
                pacf_values = []
    except Exception:
        pass

    # Confidence band untuk ACF/PACF
    confidence_band = 0.0
    try:
        if len(resid) > 0:
            confidence_band = round(1.96 / np.sqrt(len(resid)), 6)
    except Exception:
        pass

    # Prediksi
    prediksi_rp_sarima = 0.0
    try:
        forecast = sarima_model.forecast(steps=1)
        if hasattr(forecast, "iloc"):
            prediksi_rp_sarima = float(forecast.iloc[0])
        else:
            prediksi_rp_sarima = float(forecast[0])
        prediksi_rp_sarima = max(prediksi_rp_sarima, 0.0)
    except Exception:
        pass

    durasi_ms = round((time.time() - t0) * 1000, 2)

    tahap = {
        "file_model": f"sarima_{produk_id}.pkl",
        "orde": orde_str,
        "p": p, "d": d, "q": q,
        "P": sp, "D": sd, "Q": sq, "s": s,
        "adf_pvalue": round(adf_pvalue, 6) if not np.isnan(adf_pvalue) else None,
        "adf_stasioner": adf_stasioner,
        "koefisien_ar": koefisien_ar,
        "koefisien_ma": koefisien_ma,
        "koefisien_seasonal_ar": koefisien_seasonal_ar,
        "koefisien_seasonal_ma": koefisien_seasonal_ma,
        "ljung_box_pvalue": round(lb_pvalue, 6) if not np.isnan(lb_pvalue) else None,
        "prediksi_rp": round(prediksi_rp_sarima, 2),
        "durasi_ms": durasi_ms,
        "acf_values": acf_values,
        "pacf_values": pacf_values,
        "acf_lags": acf_lags,
        "confidence_band": confidence_band,
    }
    return tahap, prediksi_rp_sarima


# ─── TAHAP 4: ENSEMBLE ────────────────────────────────────────────────────────

def _tahap_4_ensemble(
    produk_id: int,
    prediksi_rp_svr: float,
    prediksi_rp_sarima: float,
    db: Session,
) -> tuple[dict, float]:
    """
    Transparansi ensemble weighting.

    Return:
      (tahap_dict, prediksi_ensemble_rp)
    """
    bobot = hitung_bobot(produk_id, db)
    w_svr    = bobot["bobot_svr"]
    w_sarima = bobot["bobot_sarima"]

    prediksi_ensemble = w_svr * prediksi_rp_svr + w_sarima * prediksi_rp_sarima
    prediksi_ensemble = max(prediksi_ensemble, 0.0)

    formula = (
        f"ŷ = {w_svr:.3f} × {prediksi_rp_svr:,.0f} + "
        f"{w_sarima:.3f} × {prediksi_rp_sarima:,.0f}"
    )

    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()
    mape_svr    = config.mape_svr    if config else None
    mape_sarima = config.mape_sarima if config else None

    tahap = {
        "mape_svr":            round(mape_svr, 4)    if mape_svr is not None else None,
        "mape_sarima":         round(mape_sarima, 4) if mape_sarima is not None else None,
        "bobot_svr":           round(w_svr, 6),
        "bobot_sarima":        round(w_sarima, 6),
        "formula":             formula,
        "prediksi_ensemble_rp": round(prediksi_ensemble, 2),
    }
    return tahap, prediksi_ensemble


# ─── TAHAP 5: KEUANGAN ────────────────────────────────────────────────────────

def _tahap_5_keuangan(
    produk_id: int,
    prediksi_ensemble: float,
    db: Session,
) -> dict:
    """
    Transparansi kalkulasi keuangan.
    """
    produk = db.query(Produk).filter(Produk.id == produk_id).first()
    if produk is None:
        return {}

    harga_beli = float(produk.harga_beli_per_unit)
    harga_jual = float(produk.harga_jual_per_unit)

    revenue_rp = prediksi_ensemble
    modal_beli_rp = prediksi_ensemble * (harga_beli / harga_jual) if harga_jual > 0 else 0.0

    is_perishable = (produk.kategori or "").lower() == "perishable"
    rugi_susut_rp = modal_beli_rp * 0.05 if is_perishable else 0.0
    kategori = "perishable" if is_perishable else "non-perishable"

    laba_bersih = revenue_rp - modal_beli_rp - rugi_susut_rp
    margin_ratio = laba_bersih / modal_beli_rp if modal_beli_rp > 0 else 0.0

    if is_perishable:
        rumus_susut = (
            f"Rugi Susut = Modal Beli × 5% = "
            f"Rp {modal_beli_rp:,.0f} × 0.05 = Rp {rugi_susut_rp:,.0f}"
        )
    else:
        rumus_susut = "Tidak ada susut (produk non-perishable)"

    return {
        "harga_beli":    round(harga_beli, 2),
        "harga_jual":    round(harga_jual, 2),
        "kategori":      kategori,
        "revenue_rp":    round(revenue_rp, 2),
        "modal_beli_rp": round(modal_beli_rp, 2),
        "rugi_susut_rp": round(rugi_susut_rp, 2),
        "margin_ratio":  round(margin_ratio, 4),
        "rumus_susut":   rumus_susut,
    }


# ─── FUNGSI UTAMA ─────────────────────────────────────────────────────────────

def buat_proses_detail(
    produk_id: int,
    tanggal: date,
    cuaca: str,
    hari_besar: str | None,
    db: Session,
) -> dict:
    """
    Susun dict transparansi 5 tahap proses ML untuk satu produk.

    Return:
      {
        produk_id, nama_produk,
        tahap_1_fitur, tahap_2_svr, tahap_3_sarima,
        tahap_4_ensemble, tahap_5_keuangan
      }

    Setiap tahap dibungkus try/except agar kegagalan satu tahap
    tidak menghentikan tahap lainnya.
    """
    produk = db.query(Produk).filter(Produk.id == produk_id).first()
    nama_produk = produk.nama_produk if produk else f"Produk #{produk_id}"

    # ── Tahap 1: Fitur ────────────────────────────────────────────────────
    tahap_1 = {}
    df_fitur = None
    kolom_fitur = []
    X_scaled = None
    scaler_x = None
    scaler_y = None
    try:
        tahap_1, df_fitur, kolom_fitur, X_scaled, scaler_x, scaler_y = _tahap_1_fitur(
            produk_id, tanggal, cuaca, hari_besar, db
        )
    except Exception as e:
        tahap_1 = {"error": str(e)}

    # ── Tahap 2: SVR ──────────────────────────────────────────────────────
    tahap_2 = {}
    prediksi_rp_svr = 0.0
    try:
        if df_fitur is not None and X_scaled is not None:
            tahap_2, prediksi_rp_svr = _tahap_2_svr(
                produk_id, df_fitur, kolom_fitur, X_scaled, scaler_x, scaler_y, db
            )
        else:
            tahap_2 = {"error": "Feature engineering gagal, SVR tidak dapat dijalankan."}
    except Exception as e:
        tahap_2 = {"error": str(e)}

    # ── Tahap 3: SARIMA ───────────────────────────────────────────────────
    tahap_3 = {}
    prediksi_rp_sarima = 0.0
    try:
        tahap_3, prediksi_rp_sarima = _tahap_3_sarima(produk_id, db)
    except Exception as e:
        tahap_3 = {"error": str(e)}

    # ── Tahap 4: Ensemble ─────────────────────────────────────────────────
    tahap_4 = {}
    prediksi_ensemble = 0.0
    try:
        tahap_4, prediksi_ensemble = _tahap_4_ensemble(
            produk_id, prediksi_rp_svr, prediksi_rp_sarima, db
        )
    except Exception as e:
        tahap_4 = {"error": str(e)}

    # ── Tahap 5: Keuangan ─────────────────────────────────────────────────
    tahap_5 = {}
    try:
        tahap_5 = _tahap_5_keuangan(produk_id, prediksi_ensemble, db)
    except Exception as e:
        tahap_5 = {"error": str(e)}

    return {
        "produk_id":        produk_id,
        "nama_produk":      nama_produk,
        "tahap_1_fitur":    tahap_1,
        "tahap_2_svr":      tahap_2,
        "tahap_3_sarima":   tahap_3,
        "tahap_4_ensemble": tahap_4,
        "tahap_5_keuangan": tahap_5,
    }
