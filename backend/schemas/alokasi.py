"""schemas/alokasi.py — Schema request/response optimisasi alokasi modal (Linear Programming)."""
from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from datetime import date
from typing import List, Optional
from enum import Enum


class StatusLP(str, Enum):
    optimal = "optimal"
    infeasible = "infeasible"


class AlokasiRequest(BaseModel):
    modal_harian_rp: float = Field(
        ...,
        ge=50_000,
        description="Total modal harian yang tersedia (Rp), minimal Rp 50.000",
    )
    prediksi_tanggal: date = Field(
        ...,
        description="Tanggal prediksi yang digunakan sebagai dasar alokasi (format: YYYY-MM-DD)",
    )

    @field_validator("modal_harian_rp")
    @classmethod
    def validasi_modal(cls, v: float) -> float:
        if v < 50_000:
            raise ValueError("Modal harian minimal Rp 50.000.")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "modal_harian_rp": 500000,
                "prediksi_tanggal": "2026-03-15",
            }
        }
    )


class AlokasiItemResponse(BaseModel):
    produk_id: int
    nama_produk: str
    alokasi_rp: float = Field(..., description="Jumlah modal yang dialokasikan untuk produk ini (Rp)")
    persentase: float = Field(..., ge=0, le=100, description="Persentase dari total modal (%)")
    estimasi_unit: float = Field(..., description="Estimasi unit yang bisa dibeli dengan alokasi ini")
    estimasi_profit_rp: float = Field(..., description="Estimasi profit bersih dari produk ini (Rp)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "produk_id": 4,
                "nama_produk": "Teri Sibolga",
                "alokasi_rp": 150000,
                "persentase": 30.0,
                "estimasi_unit": 3.33,
                "estimasi_profit_rp": 50000,
            }
        },
    )


class AlokasiResponse(BaseModel):
    modal_total_rp: float = Field(..., description="Total modal yang diinput (Rp)")
    expected_net_profit_rp: float = Field(..., description="Estimasi total profit bersih setelah alokasi optimal (Rp)")
    status_lp: StatusLP = Field(..., description="Status solver LP: optimal | infeasible")
    alokasi: List[AlokasiItemResponse]
    proses_lp: Optional[dict] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "modal_total_rp": 500000,
                "expected_net_profit_rp": 148000,
                "status_lp": "optimal",
                "alokasi": [
                    {
                        "produk_id": 4,
                        "nama_produk": "Teri Sibolga",
                        "alokasi_rp": 150000,
                        "persentase": 30.0,
                        "estimasi_unit": 3.33,
                        "estimasi_profit_rp": 50000,
                    }
                ],
            }
        }
    )
