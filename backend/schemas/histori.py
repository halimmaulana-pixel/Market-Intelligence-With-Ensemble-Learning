"""schemas/histori.py — Schema histori penjualan harian."""
from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from datetime import date
from typing import Optional
from enum import Enum


class CuacaEnum(str, Enum):
    cerah = "cerah"
    mendung = "mendung"
    hujan = "hujan"


class HistoriCreate(BaseModel):
    produk_id: int = Field(..., gt=0, description="ID produk yang dicatat penjualannya")
    tanggal: date = Field(..., description="Tanggal penjualan (format: YYYY-MM-DD)")
    penjualan_rp: float = Field(..., gt=0, description="Nilai penjualan harian (Rp), harus lebih dari 0")
    penjualan_unit: Optional[float] = Field(None, ge=0, description="Kuantitas terjual (opsional)")
    cuaca: Optional[CuacaEnum] = Field(None, description="Kondisi cuaca: cerah | mendung | hujan")
    hari_besar: Optional[str] = Field(
        None,
        max_length=100,
        description="Nama event/hari besar, atau kosongkan jika hari biasa",
    )

    @field_validator("penjualan_rp")
    @classmethod
    def validasi_penjualan(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Nilai penjualan harus lebih dari Rp 0.")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "produk_id": 1,
                "tanggal": "2026-03-11",
                "penjualan_rp": 175000,
                "penjualan_unit": None,
                "cuaca": "cerah",
                "hari_besar": None,
            }
        }
    )


class HistoriResponse(BaseModel):
    id: int
    produk_id: int
    nama_produk: str  # Di-join dari tabel produk di router
    tanggal: date
    penjualan_rp: float
    penjualan_unit: Optional[float]
    cuaca: Optional[str]
    hari_besar: Optional[str]
    is_dummy: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "produk_id": 1,
                "nama_produk": "Tahu Putih",
                "tanggal": "2025-09-13",
                "penjualan_rp": 190000,
                "penjualan_unit": None,
                "cuaca": "mendung",
                "hari_besar": None,
                "is_dummy": True,
            }
        },
    )
