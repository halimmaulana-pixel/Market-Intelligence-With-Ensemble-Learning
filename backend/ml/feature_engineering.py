"""
ml/feature_engineering.py — Feature engineering untuk pipeline SVR SalSa Market.

Fungsi utama:
  buat_fitur_svr()    — buat semua fitur dari data histori
  fit_scaler()        — fit MinMaxScaler pada fitur X
  transform_scaler()  — transform X menggunakan scaler
  inverse_transform() — denormalisasi output prediksi
  simpan_scaler()     — simpan scaler ke .pkl
  load_scaler()       — load scaler dari .pkl
"""
import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from fastapi import HTTPException

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TRAINED_MODELS_DIR

# Kolom fitur yang dihasilkan — urutan ini WAJIB konsisten saat training & prediksi
FITUR_HARI = [f"hari_{i}" for i in range(7)]          # hari_0 (Senin) … hari_6 (Minggu)
FITUR_CUACA = ["cuaca_cerah", "cuaca_mendung", "cuaca_hujan"]
FITUR_EVENT = ["is_hari_besar", "is_ramadan", "is_awal_bulan"]
FITUR_LAG = ["lag_1", "lag_7", "ma_7", "std_7"]
SEMUA_FITUR = FITUR_LAG + FITUR_HARI + FITUR_CUACA + FITUR_EVENT


# ─── FEATURE ENGINEERING ──────────────────────────────────────────────────────

def buat_fitur_svr(df: pd.DataFrame, produk_id: int) -> tuple[pd.DataFrame, list[str]]:
    """
    Buat semua fitur SVR untuk satu produk dari DataFrame histori.

    Input:
      df         — DataFrame histori penjualan (bisa berisi banyak produk)
      produk_id  — filter hanya produk ini

    Output:
      (df_fitur, nama_kolom_fitur)
      df_fitur      — DataFrame dengan kolom fitur + target (penjualan_rp)
      nama_kolom_fitur — list nama kolom fitur (tidak termasuk penjualan_rp)
    """
    # Filter produk dan urutkan ascending (WAJIB untuk time-series)
    if "produk_id" in df.columns:
        data = df[df["produk_id"] == produk_id].copy()
    else:
        data = df.copy()

    if len(data) < 8:
        raise ValueError(
            f"Data produk_id={produk_id} terlalu sedikit ({len(data)} baris). "
            "Minimal 8 baris diperlukan untuk feature engineering."
        )

    data["tanggal"] = pd.to_datetime(data["tanggal"])
    data = data.sort_values("tanggal").reset_index(drop=True)

    # ── Lag & Rolling Features ──────────────────────────────────────────────
    data["lag_1"] = data["penjualan_rp"].shift(1)
    data["lag_7"] = data["penjualan_rp"].shift(7)
    data["ma_7"]  = data["penjualan_rp"].rolling(window=7, min_periods=7).mean()
    data["std_7"] = data["penjualan_rp"].rolling(window=7, min_periods=7).std()

    # ── One-Hot: Hari Minggu (0=Senin … 6=Minggu) ──────────────────────────
    hari_idx = data["tanggal"].dt.weekday  # 0=Senin, 6=Minggu
    for i in range(7):
        data[f"hari_{i}"] = (hari_idx == i).astype(int)

    # ── One-Hot: Cuaca ──────────────────────────────────────────────────────
    cuaca_col = data["cuaca"].str.lower().fillna("cerah")
    data["cuaca_cerah"]   = (cuaca_col == "cerah").astype(int)
    data["cuaca_mendung"] = (cuaca_col == "mendung").astype(int)
    data["cuaca_hujan"]   = (cuaca_col == "hujan").astype(int)

    # ── Fitur Event ─────────────────────────────────────────────────────────
    hari_besar = data["hari_besar"].fillna("").str.strip()
    data["is_hari_besar"] = (hari_besar != "").astype(int)
    data["is_ramadan"]    = (hari_besar.str.lower() == "ramadan").astype(int)
    data["is_awal_bulan"] = (data["tanggal"].dt.day <= 5).astype(int)

    # ── Drop baris NaN (dari lag_7 dan rolling window) ──────────────────────
    data = data.dropna(subset=["lag_7", "ma_7", "std_7"]).reset_index(drop=True)

    return data, SEMUA_FITUR


# ─── SCALER ───────────────────────────────────────────────────────────────────

def fit_scaler(X: np.ndarray) -> MinMaxScaler:
    """
    Fit MinMaxScaler pada matriks fitur X.
    Mengembalikan scaler yang sudah di-fit.
    """
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.fit(X)
    return scaler


def transform_scaler(X: np.ndarray, scaler: MinMaxScaler) -> np.ndarray:
    """Transform matriks fitur X menggunakan scaler yang sudah fit."""
    return scaler.transform(X)


def inverse_transform(y_scaled: np.ndarray, scaler_target: MinMaxScaler) -> np.ndarray:
    """
    Denormalisasi nilai prediksi menggunakan scaler yang di-fit pada kolom target.
    Menangani berbagai bentuk input (1D, 2D).
    """
    y = np.array(y_scaled)
    # MinMaxScaler expects 2D input
    if y.ndim == 1:
        y = y.reshape(-1, 1)
    return scaler_target.inverse_transform(y).ravel()


# ─── SIMPAN & LOAD ────────────────────────────────────────────────────────────

def _path_scaler(produk_id: int, suffix: str = "") -> str:
    """Bangun path file scaler: trained_models/scaler_{produk_id}{suffix}.pkl"""
    os.makedirs(TRAINED_MODELS_DIR, exist_ok=True)
    return os.path.join(TRAINED_MODELS_DIR, f"scaler_{produk_id}{suffix}.pkl")


def simpan_scaler(scaler: MinMaxScaler, produk_id: int, suffix: str = "") -> str:
    """
    Simpan scaler ke file .pkl.
    suffix=""         → scaler fitur  X (scaler_{id}.pkl)
    suffix="_target"  → scaler target y (scaler_{id}_target.pkl)
    Mengembalikan path file yang disimpan.
    """
    path = _path_scaler(produk_id, suffix)
    joblib.dump(scaler, path)
    return path


def load_scaler(produk_id: int, suffix: str = "") -> MinMaxScaler:
    """
    Load scaler dari file .pkl.
    Raise HTTP 503 jika file tidak ditemukan (model belum dilatih).
    """
    path = _path_scaler(produk_id, suffix)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=503,
            detail=f"Model belum dilatih untuk produk ID {produk_id}. Hubungi Peneliti.",
        )
    return joblib.load(path)
