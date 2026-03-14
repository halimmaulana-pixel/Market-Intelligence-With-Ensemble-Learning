"""schemas/pengguna.py — Schema manajemen akun pengguna (hanya Peneliti)."""
from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum


class RoleEnum(str, Enum):
    pedagang = "pedagang"
    admin = "admin"
    peneliti = "peneliti"


class PenggunaCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username unik, minimal 3 karakter")
    password: str = Field(..., min_length=6, description="Password minimal 6 karakter")
    role: RoleEnum = Field(..., description="Level akses: pedagang | admin | peneliti")
    nama_lengkap: Optional[str] = Field(None, max_length=100, description="Nama lengkap untuk tampilan")

    @field_validator("username")
    @classmethod
    def validasi_username(cls, v: str) -> str:
        v = v.strip()
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username hanya boleh huruf, angka, underscore, dan strip.")
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "pedagang_baru",
                "password": "pass1234",
                "role": "pedagang",
                "nama_lengkap": "Ibu Sari Pedagang",
            }
        }
    )


class PenggunaUpdate(BaseModel):
    role: Optional[RoleEnum] = Field(None, description="Ubah level akses")
    nama_lengkap: Optional[str] = Field(None, max_length=100, description="Ubah nama tampilan")
    is_aktif: Optional[bool] = Field(None, description="Aktifkan atau nonaktifkan akun")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "admin",
                "nama_lengkap": "Admin Baru",
                "is_aktif": True,
            }
        }
    )


class PenggunaResponse(BaseModel):
    id: int
    username: str
    role: str
    nama_lengkap: Optional[str]
    is_aktif: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]
    created_by: Optional[int]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 3,
                "username": "pedagang",
                "role": "pedagang",
                "nama_lengkap": "Pak Budi Pedagang",
                "is_aktif": True,
                "created_at": "2026-03-01T07:00:00",
                "last_login": "2026-03-11T08:00:00",
                "created_by": 2,
            }
        },
    )
