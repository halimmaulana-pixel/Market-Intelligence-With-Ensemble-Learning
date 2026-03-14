"""
seed.py — Inisialisasi data awal database.
Idempotent: aman dijalankan berulang kali tanpa duplikat.
Isi: 8 produk default pasar Medan + 3 akun default (peneliti, admin, pedagang)
"""
import sys
import os

# Tambahkan root backend ke path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import engine, SessionLocal, Base
from database.models import Pengguna, Produk, ModelConfig
from passlib.context import CryptContext

# Setup bcrypt untuk hash password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 3 Akun default — setiap role diwakili satu akun
AKUN_DEFAULT = [
    {
        "username": "peneliti",
        "password": "peneliti123",
        "nama_lengkap": "Dr. Peneliti Utama",
        "role": "peneliti",
    },
    {
        "username": "admin",
        "password": "admin123",
        "nama_lengkap": "Admin Toko",
        "role": "admin",
    },
    {
        "username": "pedagang",
        "password": "pedagang123",
        "nama_lengkap": "Pak Budi Pedagang",
        "role": "pedagang",
    },
]

# 8 Produk default pasar tradisional Kota Medan
PRODUK_DEFAULT = [
    {
        "nama_produk": "Tahu Putih",
        "kategori": "perishable",
        "shelf_life_hari": 1,
        "harga_beli_per_unit": 1500.0,
        "harga_jual_per_unit": 2000.0,
        "satuan": "pcs",
        "min_modal_harian": 15000.0,
    },
    {
        "nama_produk": "Tahu Goreng",
        "kategori": "perishable",
        "shelf_life_hari": 1,
        "harga_beli_per_unit": 2000.0,
        "harga_jual_per_unit": 2500.0,
        "satuan": "pcs",
        "min_modal_harian": 10000.0,
    },
    {
        "nama_produk": "Toge",
        "kategori": "perishable",
        "shelf_life_hari": 1,
        "harga_beli_per_unit": 3000.0,
        "harga_jual_per_unit": 4000.0,
        "satuan": "ikat",
        "min_modal_harian": 9000.0,
    },
    {
        "nama_produk": "Teri Sibolga",
        "kategori": "semi_tahan",
        "shelf_life_hari": 7,
        "harga_beli_per_unit": 45000.0,
        "harga_jual_per_unit": 60000.0,
        "satuan": "kg",
        "min_modal_harian": 45000.0,
    },
    {
        "nama_produk": "Mie Kuning",
        "kategori": "semi_tahan",
        "shelf_life_hari": 5,
        "harga_beli_per_unit": 8000.0,
        "harga_jual_per_unit": 10000.0,
        "satuan": "bungkus",
        "min_modal_harian": 16000.0,
    },
    {
        "nama_produk": "Tempe",
        "kategori": "perishable",
        "shelf_life_hari": 2,
        "harga_beli_per_unit": 5000.0,
        "harga_jual_per_unit": 7000.0,
        "satuan": "potong",
        "min_modal_harian": 15000.0,
    },
    {
        "nama_produk": "Cabai Merah",
        "kategori": "semi_tahan",
        "shelf_life_hari": 5,
        "harga_beli_per_unit": 30000.0,
        "harga_jual_per_unit": 40000.0,
        "satuan": "kg",
        "min_modal_harian": 30000.0,
    },
    {
        "nama_produk": "Bawang Merah",
        "kategori": "tahan_lama",
        "shelf_life_hari": 14,
        "harga_beli_per_unit": 20000.0,
        "harga_jual_per_unit": 28000.0,
        "satuan": "kg",
        "min_modal_harian": 20000.0,
    },
]


def init_db():
    """Buat semua tabel berdasarkan model ORM."""
    Base.metadata.create_all(bind=engine)
    print("OK Tabel database berhasil dibuat/diverifikasi.")


def seed_akun(db):
    """Buat 3 akun default (peneliti, admin, pedagang) jika belum ada."""
    for data in AKUN_DEFAULT:
        existing = db.query(Pengguna).filter(
            Pengguna.username == data["username"]
        ).first()

        if existing:
            # Koreksi role dan nama jika berbeda (misal: akun lama punya role salah)
            if existing.role != data["role"] or existing.nama_lengkap != data["nama_lengkap"]:
                existing.role = data["role"]
                existing.nama_lengkap = data["nama_lengkap"]
                db.commit()
                print(f"  [FIX]  Akun '{data['username']}' dikoreksi -> role={data['role']}.")
            else:
                print(f"  [SKIP] Akun '{data['username']}' ({data['role']}) sudah ada.")
            continue

        akun = Pengguna(
            username=data["username"],
            password_hash=pwd_context.hash(data["password"]),
            nama_lengkap=data["nama_lengkap"],
            role=data["role"],
            is_aktif=True,
        )
        db.add(akun)
        print(f"  OK Akun '{data['username']}' ({data['role']}) berhasil dibuat.")

    db.commit()


def seed_produk(db):
    """Buat 8 produk default jika belum ada. Juga buat ModelConfig per produk."""
    for data in PRODUK_DEFAULT:
        existing = db.query(Produk).filter(
            Produk.nama_produk == data["nama_produk"]
        ).first()

        if existing:
            print(f"  [SKIP] Produk '{data['nama_produk']}' sudah ada.")
            continue

        produk = Produk(**data)
        db.add(produk)
        db.flush()  # Dapatkan ID tanpa commit penuh

        # Buat ModelConfig default untuk produk ini
        config = ModelConfig(produk_id=produk.id)
        db.add(config)
        print(f"  OK Produk '{data['nama_produk']}' + ModelConfig berhasil dibuat.")

    db.commit()


def run_seed():
    """Jalankan seluruh proses seeding."""
    print("\n=== SalSa Market - Inisialisasi Database ===")
    init_db()

    db = SessionLocal()
    try:
        print("\n[1] Seeding 3 akun default...")
        seed_akun(db)

        print("\n[2] Seeding 8 produk default pasar Medan...")
        seed_produk(db)

        print("\n=== Seeding selesai! ===")
        print("  Akun tersedia:")
        for akun in AKUN_DEFAULT:
            print(f"    [{akun['role']}] username='{akun['username']}', password='{akun['password']}'")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
