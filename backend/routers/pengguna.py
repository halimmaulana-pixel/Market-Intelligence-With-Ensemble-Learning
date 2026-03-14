"""
routers/pengguna.py — Manajemen akun pengguna.
Hanya Peneliti yang bisa membuat, mengubah, dan menonaktifkan akun.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database.db import get_db
from database.models import Pengguna
from schemas.pengguna import PenggunaCreate, PenggunaUpdate, PenggunaResponse
from auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/pengguna", tags=["Pengguna"])

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_pengguna_or_404(pengguna_id: int, db: Session) -> Pengguna:
    p = db.query(Pengguna).filter(Pengguna.id == pengguna_id).first()
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pengguna dengan ID {pengguna_id} tidak ditemukan.",
        )
    return p


# ── GET /api/pengguna ─────────────────────────────────────────────────────────

@router.get("", response_model=List[PenggunaResponse], summary="Daftar semua pengguna (hanya Peneliti)")
def list_pengguna(
    db: Session = Depends(get_db),
    _=Depends(require_role("peneliti")),
):
    """Kembalikan semua akun pengguna (aktif maupun nonaktif), diurutkan by id."""
    return db.query(Pengguna).order_by(Pengguna.id).all()


# ── GET /api/pengguna/me ──────────────────────────────────────────────────────

@router.get("/me", response_model=PenggunaResponse, summary="Profil pengguna saat ini")
def profil_saya(
    current_user: Pengguna = Depends(get_current_user),
):
    """Kembalikan data profil pengguna yang sedang login."""
    return current_user


# ── GET /api/pengguna/{id} ────────────────────────────────────────────────────

@router.get("/{pengguna_id}", response_model=PenggunaResponse, summary="Detail satu pengguna (hanya Peneliti)")
def detail_pengguna(
    pengguna_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("peneliti")),
):
    return _get_pengguna_or_404(pengguna_id, db)


# ── POST /api/pengguna ────────────────────────────────────────────────────────

@router.post("", response_model=PenggunaResponse, status_code=status.HTTP_201_CREATED,
             summary="Buat akun pengguna baru (hanya Peneliti)")
def buat_pengguna(
    body: PenggunaCreate,
    db: Session = Depends(get_db),
    current_user: Pengguna = Depends(require_role("peneliti")),
):
    """
    Buat akun baru. Username harus unik.
    Password di-hash dengan bcrypt sebelum disimpan.
    """
    existing = db.query(Pengguna).filter(Pengguna.username == body.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{body.username}' sudah digunakan.",
        )

    pengguna = Pengguna(
        username=body.username,
        password_hash=_pwd.hash(body.password),
        role=body.role.value,
        nama_lengkap=body.nama_lengkap,
        is_aktif=True,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
    )
    db.add(pengguna)
    db.commit()
    db.refresh(pengguna)
    return pengguna


# ── PUT /api/pengguna/{id} ────────────────────────────────────────────────────

@router.put("/{pengguna_id}", response_model=PenggunaResponse, summary="Update akun pengguna (hanya Peneliti)")
def update_pengguna(
    pengguna_id: int,
    body: PenggunaUpdate,
    db: Session = Depends(get_db),
    current_user: Pengguna = Depends(require_role("peneliti")),
):
    """
    Update role, nama_lengkap, atau status aktif pengguna.
    Peneliti tidak bisa menonaktifkan akunnya sendiri.
    """
    pengguna = _get_pengguna_or_404(pengguna_id, db)

    # Cegah Peneliti menonaktifkan diri sendiri
    if pengguna_id == current_user.id and body.is_aktif is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anda tidak bisa menonaktifkan akun Anda sendiri.",
        )

    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "role" and value is not None:
            setattr(pengguna, field, value.value if hasattr(value, "value") else value)
        else:
            setattr(pengguna, field, value)

    db.commit()
    db.refresh(pengguna)
    return pengguna


# ── DELETE /api/pengguna/{id} ─────────────────────────────────────────────────

@router.delete("/{pengguna_id}", summary="Nonaktifkan akun pengguna (hanya Peneliti)")
def nonaktifkan_pengguna(
    pengguna_id: int,
    db: Session = Depends(get_db),
    current_user: Pengguna = Depends(require_role("peneliti")),
):
    """
    Soft delete: set is_aktif=False.
    Peneliti tidak bisa menonaktifkan akunnya sendiri.
    """
    pengguna = _get_pengguna_or_404(pengguna_id, db)

    if pengguna_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anda tidak bisa menonaktifkan akun Anda sendiri.",
        )

    if not pengguna.is_aktif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Akun '{pengguna.username}' sudah dalam keadaan nonaktif.",
        )

    pengguna.is_aktif = False
    db.commit()

    return {"pesan": f"Akun '{pengguna.username}' berhasil dinonaktifkan."}
