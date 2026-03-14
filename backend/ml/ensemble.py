"""
ml/ensemble.py — Ensemble SVR+SARIMA dengan weighted averaging berbasis inverse MAPE.

Fungsi utama:
  hitung_bobot()          — hitung bobot adaptif w_svr & w_sarima
  prediksi_ensemble()     — prediksi satu produk, return PrediksiItemResponse
  prediksi_semua_produk() — loop semua produk aktif, return PrediksiResponse
  perlu_update_bobot()    — cek apakah bobot perlu diperbarui
  update_bobot_db()       — simpan bobot terbaru ke model_config
"""
import os
import sys
import numpy as np
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.models import Produk, ModelConfig, HistoriPenjualan
from ml.svr_model import prediksi_svr
from ml.sarima_model import prediksi_sarima
from ml.feature_engineering import SEMUA_FITUR


# ─── BOBOT ────────────────────────────────────────────────────────────────────

def hitung_bobot(produk_id: int, db: Session) -> dict:
    """
    Hitung bobot ensemble adaptif berbasis inverse MAPE.

    Formula:
      w_i = (1 / MAPE_i) / Σ(1 / MAPE_j)

    Edge cases:
      - Salah satu MAPE = None → ValueError (model belum dilatih)
      - Salah satu MAPE = 0   → bobot 1.0 untuk model tersebut, 0.0 lainnya

    Return:
      {"bobot_svr": float, "bobot_sarima": float}  — jumlahnya selalu 1.0
    """
    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()

    if config is None or config.mape_svr is None or config.mape_sarima is None:
        raise ValueError(
            f"Model untuk produk ID {produk_id} belum dilatih atau MAPE belum tersedia. "
            "Jalankan training terlebih dahulu melalui menu Konfigurasi Model."
        )

    mape_svr    = config.mape_svr
    mape_sarima = config.mape_sarima

    # Edge case: MAPE = 0 (prediksi sempurna)
    eps = 1e-10  # hindari division by zero
    if mape_svr == 0:
        return {"bobot_svr": 1.0, "bobot_sarima": 0.0}
    if mape_sarima == 0:
        return {"bobot_svr": 0.0, "bobot_sarima": 1.0}

    inv_svr    = 1.0 / (mape_svr + eps)
    inv_sarima = 1.0 / (mape_sarima + eps)
    total      = inv_svr + inv_sarima

    bobot_svr    = inv_svr    / total
    bobot_sarima = inv_sarima / total

    # Pastikan jumlah tepat 1.0 (kompensasi floating-point)
    bobot_sarima = 1.0 - bobot_svr

    return {"bobot_svr": round(bobot_svr, 6), "bobot_sarima": round(bobot_sarima, 6)}


def perlu_update_bobot(produk_id: int, db: Session) -> bool:
    """
    Return True jika bobot perlu diperbarui:
    - bobot_svr atau bobot_sarima masih None, ATAU
    - last_trained lebih dari 7 hari yang lalu
    """
    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()
    if config is None:
        return True
    if config.bobot_svr is None or config.bobot_sarima is None:
        return True
    if config.last_trained is None:
        return True
    selisih = datetime.utcnow() - config.last_trained
    return selisih.days > 7


def update_bobot_db(produk_id: int, db: Session):
    """Hitung bobot terbaru dan simpan ke tabel model_config."""
    bobot = hitung_bobot(produk_id, db)
    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()
    if config:
        config.bobot_svr    = bobot["bobot_svr"]
        config.bobot_sarima = bobot["bobot_sarima"]
        db.commit()


# ─── FITUR SVR UNTUK PREDIKSI HARI BARU ──────────────────────────────────────

def _buat_fitur_prediksi(
    produk_id: int,
    tanggal: date,
    cuaca: str,
    hari_besar: str | None,
    db: Session,
) -> dict:
    """
    Susun vektor fitur SVR untuk prediksi satu hari ke depan.
    Mengambil 7 observasi terakhir dari DB untuk menghitung lag & rolling stats.
    """
    # Ambil 7 baris terakhir untuk produk ini
    rows = (
        db.query(HistoriPenjualan)
        .filter(HistoriPenjualan.produk_id == produk_id)
        .order_by(HistoriPenjualan.tanggal.desc())
        .limit(7)
        .all()
    )

    if len(rows) < 7:
        raise ValueError(
            f"Data histori produk ID {produk_id} tidak cukup ({len(rows)} baris). "
            "Minimal 7 baris diperlukan untuk prediksi."
        )

    # Sort ascending (rows diambil descending di atas)
    rows_asc = sorted(rows, key=lambda r: r.tanggal)
    y_recent = np.array([r.penjualan_rp for r in rows_asc], dtype=float)

    lag_1 = float(y_recent[-1])
    lag_7 = float(y_recent[0])         # observasi 7 hari lalu
    ma_7  = float(np.mean(y_recent))
    std_7 = float(np.std(y_recent, ddof=1)) if len(y_recent) > 1 else 0.0

    # One-hot hari minggu (0=Senin … 6=Minggu)
    hari_idx = tanggal.weekday()
    hari_dict = {f"hari_{i}": 1 if i == hari_idx else 0 for i in range(7)}

    # One-hot cuaca
    cuaca_norm = (cuaca or "cerah").lower().strip()
    cuaca_dict = {
        "cuaca_cerah":   1 if cuaca_norm == "cerah"   else 0,
        "cuaca_mendung": 1 if cuaca_norm == "mendung" else 0,
        "cuaca_hujan":   1 if cuaca_norm == "hujan"   else 0,
    }

    # Fitur event
    hb = (hari_besar or "").strip()
    is_hari_besar = 1 if hb else 0
    is_ramadan    = 1 if "ramadan" in hb.lower() else 0
    is_awal_bulan = 1 if tanggal.day <= 5 else 0

    return {
        "lag_1": lag_1, "lag_7": lag_7, "ma_7": ma_7, "std_7": std_7,
        **hari_dict,
        **cuaca_dict,
        "is_hari_besar": is_hari_besar,
        "is_ramadan":    is_ramadan,
        "is_awal_bulan": is_awal_bulan,
    }


# ─── PREDIKSI ENSEMBLE ────────────────────────────────────────────────────────

def prediksi_ensemble(
    produk_id: int,
    tanggal: date,
    cuaca: str,
    hari_besar: str | None,
    db: Session,
) -> dict:
    """
    Prediksi ensemble SVR+SARIMA untuk satu produk, satu hari ke depan.

    Return dict kompatibel dengan PrediksiItemResponse:
      produk_id, nama_produk, prediksi_svr_rp, prediksi_sarima_rp,
      prediksi_ensemble_rp, bobot_svr, bobot_sarima,
      modal_beli_rp, revenue_rp, rugi_susut_rp, margin_ratio
    """
    # ── Ambil info produk ──────────────────────────────────────────────────
    produk = db.query(Produk).filter(Produk.id == produk_id).first()
    if produk is None:
        raise ValueError(f"Produk ID {produk_id} tidak ditemukan.")

    # ── Fitur SVR untuk hari prediksi ─────────────────────────────────────
    fitur_input = _buat_fitur_prediksi(produk_id, tanggal, cuaca, hari_besar, db)

    # ── Prediksi individual ───────────────────────────────────────────────
    y_svr    = prediksi_svr(produk_id, fitur_input, db)
    y_sarima = prediksi_sarima(produk_id, db, steps=1)

    # ── Hitung bobot & ensemble ───────────────────────────────────────────
    bobot = hitung_bobot(produk_id, db)
    w_svr    = bobot["bobot_svr"]
    w_sarima = bobot["bobot_sarima"]

    y_ensemble = w_svr * y_svr + w_sarima * y_sarima
    y_ensemble = max(y_ensemble, 0.0)

    # ── Variabel keuangan ─────────────────────────────────────────────────
    harga_beli = produk.harga_beli_per_unit
    harga_jual = produk.harga_jual_per_unit

    # y_ensemble adalah revenue (Rp) = unit × harga_jual
    # modal_beli = unit × harga_beli = y_ensemble × (harga_beli / harga_jual)
    modal_beli_rp = y_ensemble * (harga_beli / harga_jual) if harga_jual > 0 else 0.0

    revenue_rp = y_ensemble

    # Susut hanya untuk produk perishable (5% dari modal beli)
    rugi_susut_rp = modal_beli_rp * 0.05 if produk.kategori == "perishable" else 0.0

    # margin_ratio = (revenue - modal_beli - susut) / modal_beli
    laba_bersih = revenue_rp - modal_beli_rp - rugi_susut_rp
    margin_ratio = laba_bersih / modal_beli_rp if modal_beli_rp > 0 else 0.0

    return {
        "produk_id":            produk_id,
        "nama_produk":          produk.nama_produk,
        "prediksi_svr_rp":      round(y_svr, 2),
        "prediksi_sarima_rp":   round(y_sarima, 2),
        "prediksi_ensemble_rp": round(y_ensemble, 2),
        "bobot_svr":            w_svr,
        "bobot_sarima":         w_sarima,
        "modal_beli_rp":        round(modal_beli_rp, 2),
        "revenue_rp":           round(revenue_rp, 2),
        "rugi_susut_rp":        round(rugi_susut_rp, 2),
        "margin_ratio":         round(margin_ratio, 4),
    }


def prediksi_semua_produk(
    tanggal: date,
    cuaca: str,
    hari_besar: str | None,
    produk_ids: list[int] | None,
    db: Session,
) -> dict:
    """
    Prediksi ensemble untuk semua produk aktif (atau subset produk_ids).

    Error per produk ditangani secara individual — satu produk gagal
    tidak menghentikan prediksi produk lainnya.

    Return dict kompatibel dengan PrediksiResponse:
      {"tanggal": date, "prediksi": [PrediksiItemResponse, ...]}
    """
    # Ambil semua produk aktif
    query = db.query(Produk).filter(Produk.is_aktif == True)
    if produk_ids:
        query = query.filter(Produk.id.in_(produk_ids))
    produk_list = query.all()

    hasil_prediksi = []
    for produk in produk_list:
        try:
            item = prediksi_ensemble(
                produk_id=produk.id,
                tanggal=tanggal,
                cuaca=cuaca,
                hari_besar=hari_besar,
                db=db,
            )
            hasil_prediksi.append(item)
        except Exception as e:
            # Log warning tapi jangan gagalkan semua
            print(f"[ENSEMBLE] WARNING produk_id={produk.id} ({produk.nama_produk}) — {e}")

    return {
        "tanggal":  tanggal,
        "prediksi": hasil_prediksi,
    }
