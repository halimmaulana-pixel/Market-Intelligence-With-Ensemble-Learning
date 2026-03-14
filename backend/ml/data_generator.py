"""
data_generator.py — Generate 180 hari data penjualan dummy realistis untuk
8 produk pasar tradisional Kota Medan.

Dijalankan SEKALI saat setup awal. Output:
  1. data/data_dummy.csv
  2. Insert ke tabel histori_penjualan (is_dummy=True)

Pola yang diimplementasikan:
  - Seasonality mingguan (Sabtu puncak, Senin terendah)
  - Efek cuaca acak (Cerah 60%, Mendung 25%, Hujan 15%)
  - Efek event: Ramadan, Idul Fitri, Awal Bulan
  - Gaussian noise ±8%
"""
import sys
import os
import random
import math
from datetime import date, timedelta

import pandas as pd
import numpy as np

# Tambahkan root backend ke path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import SessionLocal
from database.models import HistoriPenjualan, Produk

# ─── KONFIGURASI ──────────────────────────────────────────────────────────────

# Tanggal akhir = hari ini, mundur 180 hari
TANGGAL_AKHIR = date.today()
TANGGAL_MULAI = TANGGAL_AKHIR - timedelta(days=179)

# Baseline penjualan harian (Rp) per produk
BASELINE_PENJUALAN = {
    "Tahu Putih":   150_000,
    "Tahu Goreng":  120_000,
    "Toge":          80_000,
    "Teri Sibolga": 600_000,
    "Mie Kuning":   200_000,
    "Tempe":        180_000,
    "Cabai Merah":  450_000,
    "Bawang Merah": 350_000,
}

# Faktor pengali seasonality mingguan (0=Senin, 6=Minggu)
FAKTOR_HARI = {
    0: 0.85,  # Senin
    1: 0.90,  # Selasa
    2: 0.95,  # Rabu
    3: 1.00,  # Kamis (baseline)
    4: 1.25,  # Jumat
    5: 1.35,  # Sabtu (puncak)
    6: 1.20,  # Minggu
}

# Distribusi cuaca & faktor pengali
CUACA_OPSI = ["cerah", "mendung", "hujan"]
CUACA_PROB = [0.60, 0.25, 0.15]
FAKTOR_CUACA = {
    "cerah":   1.00,
    "mendung": 0.92,
    "hujan":   0.80,
}

# ─── PERIODE EVENT ────────────────────────────────────────────────────────────

# Ramadan 1447 H (estimasi 17 Feb – 17 Mar 2026)
RAMADAN_MULAI = date(2026, 2, 17)
RAMADAN_SELESAI = date(2026, 3, 17)

# Idul Fitri 1447 H: ~18 Mar 2026 → H-3 s/d H+1
IDUL_FITRI = date(2026, 3, 18)
IDUL_FITRI_MULAI = IDUL_FITRI - timedelta(days=3)
IDUL_FITRI_SELESAI = IDUL_FITRI + timedelta(days=1)

# Produk yang terdampak Ramadan (nama → faktor tambahan)
RAMADAN_EFEK = {
    "Teri Sibolga": 1.40,  # +40%
    "Tahu Putih":   1.20,  # +20%
    "Tahu Goreng":  1.20,
    "Tempe":        1.20,
}


# ─── FUNGSI UTAMA ─────────────────────────────────────────────────────────────

def hitung_faktor_event(tanggal: date, nama_produk: str) -> tuple[float, str | None]:
    """
    Hitung faktor pengali event dan label hari besar untuk suatu tanggal.
    Mengembalikan (faktor, label_hari_besar).
    Prioritas: Idul Fitri > Ramadan > Awal Bulan > Normal
    """
    # Idul Fitri (H-3 s/d H+1) — semua produk +50-70%
    if IDUL_FITRI_MULAI <= tanggal <= IDUL_FITRI_SELESAI:
        faktor = random.uniform(1.50, 1.70)
        return faktor, "Idul Fitri"

    # Ramadan — hanya produk tertentu yang naik signifikan
    if RAMADAN_MULAI <= tanggal <= RAMADAN_SELESAI:
        faktor = RAMADAN_EFEK.get(nama_produk, 1.05)  # produk lain naik sedikit
        return faktor, "Ramadan"

    # Awal bulan (tanggal 1-5) — semua produk +15%
    if tanggal.day <= 5:
        return 1.15, "Awal Bulan"

    return 1.00, None


def generate_satu_baris(
    tanggal: date,
    nama_produk: str,
    baseline: float,
    cuaca: str,
) -> float:
    """
    Hitung penjualan_rp untuk satu produk pada satu hari.
    Formula: baseline × faktor_hari × faktor_cuaca × faktor_event × noise
    """
    f_hari = FAKTOR_HARI[tanggal.weekday()]
    f_cuaca = FAKTOR_CUACA[cuaca]
    f_event, _ = hitung_faktor_event(tanggal, nama_produk)

    # Gaussian noise ±8% (std = 0.08/2 ≈ 0.04 agar ≤3σ = ±12%)
    noise = np.random.normal(loc=1.0, scale=0.04)
    noise = max(0.80, min(1.20, noise))  # clamp agar tidak ekstrem

    penjualan = baseline * f_hari * f_cuaca * f_event * noise

    # Bulatkan ke ratusan terdekat (realistis untuk pasar)
    return round(penjualan / 100) * 100


def generate_semua_data() -> pd.DataFrame:
    """Generate DataFrame 180 hari × 8 produk = 1.440 baris."""
    np.random.seed(42)  # reproducible
    random.seed(42)

    rows = []
    tanggal_range = [
        TANGGAL_MULAI + timedelta(days=i)
        for i in range((TANGGAL_AKHIR - TANGGAL_MULAI).days + 1)
    ]

    for tanggal in tanggal_range:
        # Pilih cuaca hari ini (sama untuk semua produk di hari yang sama)
        cuaca = random.choices(CUACA_OPSI, weights=CUACA_PROB, k=1)[0]
        _, label_hari_besar = hitung_faktor_event(tanggal, "")

        for nama_produk, baseline in BASELINE_PENJUALAN.items():
            penjualan = generate_satu_baris(tanggal, nama_produk, baseline, cuaca)
            rows.append({
                "tanggal": tanggal.isoformat(),
                "nama_produk": nama_produk,
                "penjualan_rp": penjualan,
                "cuaca": cuaca,
                "hari_besar": label_hari_besar,
                "is_dummy": True,
            })

    return pd.DataFrame(rows)


# ─── SIMPAN & IMPORT ──────────────────────────────────────────────────────────

def simpan_csv(df: pd.DataFrame, path: str = "data/data_dummy.csv"):
    """Simpan DataFrame ke CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"OK CSV tersimpan: {path} ({len(df)} baris)")


def import_ke_db(df: pd.DataFrame):
    """
    Import data dummy ke tabel histori_penjualan.
    Idempotent: hapus data is_dummy=True dulu sebelum insert ulang.
    """
    db = SessionLocal()
    try:
        # Ambil mapping nama_produk → produk_id dari DB
        produk_list = db.query(Produk).filter(Produk.is_aktif == True).all()
        produk_map = {p.nama_produk: p.id for p in produk_list}

        # Hapus data dummy lama agar tidak duplikat
        hapus = db.query(HistoriPenjualan).filter(HistoriPenjualan.is_dummy == True)
        jumlah_hapus = hapus.count()
        hapus.delete()
        db.commit()
        if jumlah_hapus > 0:
            print(f"  [RESET] {jumlah_hapus} baris dummy lama dihapus.")

        # Insert data baru
        batch = []
        for _, row in df.iterrows():
            produk_id = produk_map.get(row["nama_produk"])
            if produk_id is None:
                print(f"  [SKIP] Produk '{row['nama_produk']}' tidak ditemukan di DB.")
                continue

            batch.append(HistoriPenjualan(
                produk_id=produk_id,
                tanggal=date.fromisoformat(row["tanggal"]),
                penjualan_rp=float(row["penjualan_rp"]),
                cuaca=row["cuaca"],
                hari_besar=row["hari_besar"] if pd.notna(row["hari_besar"]) else None,
                is_dummy=True,
            ))

        db.bulk_save_objects(batch)
        db.commit()
        print(f"  OK {len(batch)} baris berhasil di-insert ke histori_penjualan.")
    finally:
        db.close()


def tampilkan_statistik(df: pd.DataFrame):
    """Tampilkan sample 5 baris dan statistik ringkas per produk."""
    print("\n─── Sample 5 Baris Pertama ───")
    print(df.head(5).to_string(index=False))

    print("\n─── Statistik Penjualan per Produk (Rp) ───")
    stat = df.groupby("nama_produk")["penjualan_rp"].agg(
        mean="mean", min="min", max="max", std="std"
    ).reset_index()
    stat["mean"] = stat["mean"].apply(lambda x: f"Rp {x:,.0f}")
    stat["min"]  = stat["min"].apply(lambda x: f"Rp {x:,.0f}")
    stat["max"]  = stat["max"].apply(lambda x: f"Rp {x:,.0f}")
    stat["std"]  = stat["std"].apply(lambda x: f"Rp {x:,.0f}")
    print(stat.to_string(index=False))

    print("\n─── Distribusi Cuaca ───")
    print(df[["tanggal","cuaca"]].drop_duplicates("tanggal")["cuaca"].value_counts().to_string())

    print("\n─── Jumlah Hari Besar ───")
    hb = df[["tanggal","hari_besar"]].drop_duplicates("tanggal")
    print(hb["hari_besar"].fillna("(normal)").value_counts().to_string())

    print(f"\n─── Total Baris ───")
    print(f"  {len(df)} baris ({df['tanggal'].nunique()} hari × {df['nama_produk'].nunique()} produk)")


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def run():
    print("\n=== SalSa Market — Generate Data Dummy ===")
    print(f"  Periode: {TANGGAL_MULAI} s/d {TANGGAL_AKHIR} (180 hari)")

    print("\n[1] Generating data...")
    df = generate_semua_data()

    print("\n[2] Menyimpan CSV...")
    simpan_csv(df)

    print("\n[3] Import ke database...")
    import_ke_db(df)

    print("\n[4] Verifikasi output:")
    tampilkan_statistik(df)

    print("\n=== Generate data dummy selesai! ===")


if __name__ == "__main__":
    run()
