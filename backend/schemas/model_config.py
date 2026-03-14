"""schemas/model_config.py — Schema konfigurasi parameter ML dan status training."""
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from datetime import datetime
from typing import Optional


class ModelConfigResponse(BaseModel):
    id: int
    produk_id: int
    nama_produk: str  # Di-join dari tabel produk di router

    # Parameter SVR
    svr_C: float
    svr_gamma: float
    svr_epsilon: float

    # Parameter SARIMA non-seasonal
    sarima_p: int
    sarima_d: int
    sarima_q: int

    # Parameter SARIMA seasonal (kolom DB: sarima_sp/sd/sq)
    sarima_sp: int = Field(..., description="Orde AR seasonal (P)")
    sarima_sd: int = Field(..., description="Orde differencing seasonal (D)")
    sarima_sq: int = Field(..., description="Orde MA seasonal (Q)")
    sarima_s: int = Field(..., description="Periode musiman (default 7 = mingguan)")

    auto_tune: bool

    # Hasil evaluasi
    mape_svr: Optional[float]
    mape_sarima: Optional[float]
    bobot_svr: Optional[float]
    bobot_sarima: Optional[float]

    # Status
    last_trained: Optional[datetime]
    model_tersedia: bool
    trained_by: Optional[int] = Field(None, description="ID peneliti yang terakhir melakukan training")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "produk_id": 1,
                "nama_produk": "Tahu Putih",
                "svr_C": 10.0,
                "svr_gamma": 0.1,
                "svr_epsilon": 0.1,
                "sarima_p": 1,
                "sarima_d": 1,
                "sarima_q": 1,
                "sarima_sp": 1,
                "sarima_sd": 1,
                "sarima_sq": 1,
                "sarima_s": 7,
                "auto_tune": True,
                "mape_svr": 8.5,
                "mape_sarima": 11.2,
                "bobot_svr": 0.57,
                "bobot_sarima": 0.43,
                "last_trained": "2026-03-10T09:00:00",
                "model_tersedia": True,
                "trained_by": 2,
            }
        },
    )


class ModelConfigUpdate(BaseModel):
    # Parameter SVR — semua opsional
    svr_C: Optional[float] = Field(None, gt=0, description="Regularisasi C (>0)")
    svr_gamma: Optional[float] = Field(None, gt=0, description="Parameter kernel γ (>0)")
    svr_epsilon: Optional[float] = Field(None, gt=0, description="Lebar tube ε (>0)")

    # Parameter SARIMA non-seasonal
    sarima_p: Optional[int] = Field(None, ge=0, le=5, description="AR non-seasonal (0–5)")
    sarima_d: Optional[int] = Field(None, ge=0, le=2, description="Differencing non-seasonal (0–2)")
    sarima_q: Optional[int] = Field(None, ge=0, le=5, description="MA non-seasonal (0–5)")

    # Parameter SARIMA seasonal
    sarima_sp: Optional[int] = Field(None, ge=0, le=2, description="AR seasonal P (0–2)")
    sarima_sd: Optional[int] = Field(None, ge=0, le=2, description="Differencing seasonal D (0–2)")
    sarima_sq: Optional[int] = Field(None, ge=0, le=2, description="MA seasonal Q (0–2)")
    sarima_s: Optional[int] = Field(None, ge=2, description="Periode musiman (minimal 2)")

    auto_tune: Optional[bool] = Field(None, description="True = GridSearch/auto_arima otomatis")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "svr_C": 50.0,
                "svr_gamma": 0.01,
                "svr_epsilon": 0.05,
                "sarima_p": 2,
                "sarima_d": 1,
                "sarima_q": 1,
                "sarima_sp": 1,
                "sarima_sd": 1,
                "sarima_sq": 1,
                "sarima_s": 7,
                "auto_tune": False,
            }
        }
    )


class TrainingResponse(BaseModel):
    status: str = Field(..., description="Hasil training: berhasil | gagal | berjalan")
    pesan: str = Field(..., description="Pesan detail status training")
    produk_dilatih: int = Field(..., description="Jumlah produk yang berhasil dilatih")
    durasi_detik: float = Field(..., description="Total waktu training dalam detik")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "berhasil",
                "pesan": "Model SVR dan SARIMA berhasil dilatih untuk 8 produk.",
                "produk_dilatih": 8,
                "durasi_detik": 42.7,
            }
        }
    )
