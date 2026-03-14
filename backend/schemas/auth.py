"""schemas/auth.py — Schema autentikasi dan manajemen sesi."""
from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from datetime import datetime
from typing import Optional


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, description="Username akun")
    password: str = Field(..., min_length=1, description="Password akun")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"username": "peneliti", "password": "peneliti123"}
        }
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    nama_lengkap: Optional[str]
    username: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGci...",
                "token_type": "bearer",
                "role": "peneliti",
                "nama_lengkap": "Dr. Peneliti Utama",
                "username": "peneliti",
            }
        }
    )


class GantiPasswordRequest(BaseModel):
    password_lama: str = Field(..., min_length=1, description="Password lama Anda")
    password_baru: str = Field(
        ...,
        min_length=6,
        description="Password baru minimal 6 karakter",
    )

    @field_validator("password_baru")
    @classmethod
    def validasi_password_baru(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password baru minimal 6 karakter.")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "password_lama": "admin123",
                "password_baru": "passwordbaru456",
            }
        }
    )


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    nama_lengkap: Optional[str]
    is_aktif: bool
    last_login: Optional[datetime]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 2,
                "username": "peneliti",
                "role": "peneliti",
                "nama_lengkap": "Dr. Peneliti Utama",
                "is_aktif": True,
                "last_login": "2026-03-11T08:00:00",
            }
        },
    )
