from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.db import Base


class Pengguna(Base):
    """Model akun pengguna dengan 3 level role."""
    __tablename__ = "pengguna"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)  # bcrypt hash — JANGAN plain text
    nama_lengkap = Column(String, nullable=True)
    role = Column(String, nullable=False)  # pedagang | admin | peneliti
    is_aktif = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("pengguna.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime, nullable=True)

    # Relasi: siapa yang membuat akun ini
    pembuat = relationship("Pengguna", remote_side=[id], foreign_keys=[created_by])


class Produk(Base):
    """Model produk pasar yang diprediksi dan dialokasikan modalnya."""
    __tablename__ = "produk"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nama_produk = Column(String, nullable=False, unique=True)
    kategori = Column(String, nullable=True)  # perishable | semi_tahan | tahan_lama
    shelf_life_hari = Column(Integer, nullable=True)
    harga_beli_per_unit = Column(Float, nullable=False)
    harga_jual_per_unit = Column(Float, nullable=False)
    satuan = Column(String, nullable=True)  # kg | ikat | bungkus | pcs | potong | lainnya
    min_modal_harian = Column(Float, default=0.0)  # Minimum alokasi LP
    is_aktif = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relasi
    histori = relationship("HistoriPenjualan", back_populates="produk")
    model_config = relationship("ModelConfig", back_populates="produk", uselist=False)


class HistoriPenjualan(Base):
    """Riwayat penjualan harian per produk."""
    __tablename__ = "histori_penjualan"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    produk_id = Column(Integer, ForeignKey("produk.id"), nullable=False)
    tanggal = Column(Date, nullable=False)
    penjualan_rp = Column(Float, nullable=False)
    penjualan_unit = Column(Float, nullable=True)
    cuaca = Column(String, nullable=True)  # cerah | mendung | hujan
    hari_besar = Column(Text, nullable=True)  # Nama event atau NULL
    is_dummy = Column(Boolean, default=False)  # TRUE = data generated

    # Relasi
    produk = relationship("Produk", back_populates="histori")


class ModelConfig(Base):
    """Konfigurasi parameter ML per produk (one-to-one dengan Produk)."""
    __tablename__ = "model_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    produk_id = Column(Integer, ForeignKey("produk.id"), unique=True, nullable=False)

    # Parameter SVR
    svr_C = Column(Float, default=10.0)
    svr_gamma = Column(Float, default=0.1)
    svr_epsilon = Column(Float, default=0.1)

    # Parameter SARIMA non-seasonal (p,d,q)
    sarima_p = Column(Integer, default=1)
    sarima_d = Column(Integer, default=1)
    sarima_q = Column(Integer, default=1)
    # Parameter SARIMA seasonal (P,D,Q,s) — pakai prefix sp/sd/sq agar tidak konflik dengan SQLite case-insensitive
    sarima_sp = Column(Integer, default=1)  # seasonal P
    sarima_sd = Column(Integer, default=1)  # seasonal D
    sarima_sq = Column(Integer, default=1)  # seasonal Q
    sarima_s = Column(Integer, default=7)   # periode musiman mingguan

    # Toggle auto-tuning
    auto_tune = Column(Boolean, default=True)

    # Hasil evaluasi
    mape_svr = Column(Float, nullable=True)
    mape_sarima = Column(Float, nullable=True)
    bobot_svr = Column(Float, nullable=True)
    bobot_sarima = Column(Float, nullable=True)

    # Status model
    last_trained = Column(DateTime, nullable=True)
    model_tersedia = Column(Boolean, default=False)
    trained_by = Column(Integer, ForeignKey("pengguna.id"), nullable=True)  # FK: peneliti yang trigger training

    # Relasi
    produk = relationship("Produk", back_populates="model_config")
    pelatih = relationship("Pengguna", foreign_keys=[trained_by])
