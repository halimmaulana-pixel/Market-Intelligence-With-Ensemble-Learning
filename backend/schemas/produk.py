"""schemas/produk.py — Schema manajemen produk dan harga."""
from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum


class KategoriEnum(str, Enum):
    perishable = "perishable"
    semi_tahan = "semi_tahan"
    tahan_lama = "tahan_lama"


class SatuanEnum(str, Enum):
    kg = "kg"
    ikat = "ikat"
    bungkus = "bungkus"
    pcs = "pcs"
    potong = "potong"
    lainnya = "lainnya"


class ProdukCreate(BaseModel):
    nama_produk: str = Field(..., min_length=2, max_length=100, description="Nama produk, harus unik")
    kategori: KategoriEnum = Field(..., description="perishable | semi_tahan | tahan_lama")
    shelf_life_hari: int = Field(..., ge=1, description="Umur simpan minimal 1 hari")
    harga_beli_per_unit: float = Field(..., gt=0, description="Harga beli per satuan (Rp), harus lebih dari 0")
    harga_jual_per_unit: float = Field(..., gt=0, description="Harga jual per satuan (Rp), harus lebih dari 0")
    satuan: SatuanEnum = Field(..., description="Satuan: kg | ikat | bungkus | pcs | potong | lainnya")
    min_modal_harian: float = Field(0.0, ge=0, description="Minimum alokasi modal harian untuk LP (Rp)")

    @field_validator("harga_jual_per_unit")
    @classmethod
    def validasi_harga_jual(cls, v: float, info) -> float:
        harga_beli = info.data.get("harga_beli_per_unit", 0)
        if harga_beli and v <= harga_beli:
            raise ValueError("Harga jual harus lebih besar dari harga beli.")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nama_produk": "Tahu Sutra",
                "kategori": "perishable",
                "shelf_life_hari": 1,
                "harga_beli_per_unit": 2000,
                "harga_jual_per_unit": 2800,
                "satuan": "pcs",
                "min_modal_harian": 10000,
            }
        }
    )


class ProdukUpdate(BaseModel):
    nama_produk: Optional[str] = Field(None, min_length=2, max_length=100)
    kategori: Optional[KategoriEnum] = None
    shelf_life_hari: Optional[int] = Field(None, ge=1)
    harga_beli_per_unit: Optional[float] = Field(None, gt=0)
    harga_jual_per_unit: Optional[float] = Field(None, gt=0)
    satuan: Optional[SatuanEnum] = None
    min_modal_harian: Optional[float] = Field(None, ge=0)
    is_aktif: Optional[bool] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "harga_beli_per_unit": 1800,
                "harga_jual_per_unit": 2500,
            }
        }
    )


class ProdukResponse(BaseModel):
    id: int
    nama_produk: str
    kategori: Optional[str]
    shelf_life_hari: Optional[int]
    harga_beli_per_unit: float
    harga_jual_per_unit: float
    satuan: Optional[str]
    min_modal_harian: float
    is_aktif: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "nama_produk": "Tahu Putih",
                "kategori": "perishable",
                "shelf_life_hari": 1,
                "harga_beli_per_unit": 1500,
                "harga_jual_per_unit": 2000,
                "satuan": "pcs",
                "min_modal_harian": 15000,
                "is_aktif": True,
                "created_at": "2026-03-01T07:00:00",
                "updated_at": "2026-03-01T07:00:00",
            }
        },
    )
