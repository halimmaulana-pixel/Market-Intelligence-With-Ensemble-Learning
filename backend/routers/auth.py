"""
routers/auth.py — Endpoint autentikasi: login, logout, info user, ganti password.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from passlib.context import CryptContext
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_db
from database.models import Pengguna
from auth.jwt_handler import create_access_token
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Autentikasi"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login", summary="Login dan dapatkan JWT token")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login dengan username dan password.
    Mengembalikan JWT access token dan info dasar user.
    """
    user = db.query(Pengguna).filter(
        Pengguna.username == form_data.username
    ).first()

    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah.",
        )

    if not user.is_aktif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda telah dinonaktifkan. Hubungi Peneliti.",
        )

    # Update waktu login terakhir
    user.last_login = datetime.utcnow()
    db.commit()

    # Buat token dengan payload: sub=user_id, role, username
    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "nama_lengkap": user.nama_lengkap,
        "username": user.username,
    }


@router.post("/logout", summary="Logout (invalidasi sesi sisi klien)")
def logout(current_user: Pengguna = Depends(get_current_user)):
    """
    Logout — JWT stateless, invalidasi dilakukan di sisi frontend
    (hapus token dari localStorage). Endpoint ini sebagai konfirmasi.
    """
    return {"pesan": f"Sampai jumpa, {current_user.nama_lengkap}! Sesi telah diakhiri."}


@router.get("/me", summary="Informasi akun yang sedang login")
def get_me(current_user: Pengguna = Depends(get_current_user)):
    """Kembalikan data profil user yang sedang login."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "nama_lengkap": current_user.nama_lengkap,
        "role": current_user.role,
        "last_login": current_user.last_login,
    }


@router.put("/ganti-password", summary="Ganti password akun sendiri")
def ganti_password(
    body: dict,
    db: Session = Depends(get_db),
    current_user: Pengguna = Depends(get_current_user),
):
    """
    Ganti password akun yang sedang login.
    Body: { "password_lama": "...", "password_baru": "..." }
    """
    password_lama = body.get("password_lama", "")
    password_baru = body.get("password_baru", "")

    if not pwd_context.verify(password_lama, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password lama tidak sesuai.",
        )

    if len(password_baru) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru minimal 6 karakter.",
        )

    current_user.password_hash = pwd_context.hash(password_baru)
    db.commit()

    return {"pesan": "Password berhasil diperbarui."}
