"""schemas/prediksi.py — Schema request/response prediksi ensemble SVR+SARIMA."""
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from datetime import date
from typing import Optional, List
from enum import Enum


class CuacaEnum(str, Enum):
    cerah = "cerah"
    mendung = "mendung"
    hujan = "hujan"


class PrediksiRequest(BaseModel):
    tanggal: date = Field(..., description="Tanggal prediksi (format: YYYY-MM-DD)")
    cuaca: CuacaEnum = Field(..., description="Kondisi cuaca: cerah | mendung | hujan")
    hari_besar: Optional[str] = Field(
        None,
        max_length=100,
        description="Nama event/hari besar, atau kosongkan jika hari biasa",
    )
    produk_ids: Optional[List[int]] = Field(
        None,
        description="Daftar produk_id yang diprediksi. Kosongkan untuk semua produk aktif.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tanggal": "2026-03-15",
                "cuaca": "cerah",
                "hari_besar": None,
                "produk_ids": None,
            }
        }
    )


class PrediksiItemResponse(BaseModel):
    produk_id: int
    nama_produk: str
    prediksi_svr_rp: float = Field(..., description="Prediksi penjualan oleh model SVR (Rp)")
    prediksi_sarima_rp: float = Field(..., description="Prediksi penjualan oleh model SARIMA (Rp)")
    prediksi_ensemble_rp: float = Field(..., description="Prediksi ensemble gabungan (Rp)")
    bobot_svr: float = Field(..., ge=0, le=1, description="Bobot SVR dalam ensemble (0–1)")
    bobot_sarima: float = Field(..., ge=0, le=1, description="Bobot SARIMA dalam ensemble (0–1)")
    modal_beli_rp: float = Field(..., description="Estimasi modal beli yang dibutuhkan (Rp)")
    revenue_rp: float = Field(..., description="Estimasi pendapatan (Rp)")
    rugi_susut_rp: float = Field(..., description="Estimasi kerugian susut untuk produk perishable (Rp)")
    margin_ratio: float = Field(..., description="Rasio margin bersih (0–1)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "produk_id": 1,
                "nama_produk": "Tahu Putih",
                "prediksi_svr_rp": 145000,
                "prediksi_sarima_rp": 138000,
                "prediksi_ensemble_rp": 142350,
                "bobot_svr": 0.60,
                "bobot_sarima": 0.40,
                "modal_beli_rp": 106763,
                "revenue_rp": 142350,
                "rugi_susut_rp": 5338,
                "margin_ratio": 0.284,
            }
        },
    )


class PrediksiResponse(BaseModel):
    tanggal: date
    prediksi: List[PrediksiItemResponse]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tanggal": "2026-03-15",
                "prediksi": [
                    {
                        "produk_id": 1,
                        "nama_produk": "Tahu Putih",
                        "prediksi_ensemble_rp": 142350,
                        "bobot_svr": 0.60,
                        "bobot_sarima": 0.40,
                        "modal_beli_rp": 106763,
                        "revenue_rp": 142350,
                        "rugi_susut_rp": 5338,
                        "margin_ratio": 0.284,
                    }
                ],
            }
        }
    )


class ProsesDetailResponse(BaseModel):
    produk_id: int
    nama_produk: str
    tahap_1_fitur: dict
    tahap_2_svr: dict
    tahap_3_sarima: dict
    tahap_4_ensemble: dict
    tahap_5_keuangan: dict

    model_config = ConfigDict(from_attributes=True)


class VerbosePrediksiResponse(PrediksiResponse):
    proses_detail: List[ProsesDetailResponse] = []
