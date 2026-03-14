"""
dependencies.py — FastAPI dependency injection untuk autentikasi dan otorisasi role.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import get_db
from database.models import Pengguna
from auth.jwt_handler import decode_token

# Skema OAuth2: token diambil dari header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Pengguna:
    """
    Dependency: ambil user yang sedang login dari JWT token.
    Raise HTTP 401 jika token tidak valid.
    Raise HTTP 403 jika akun dinonaktifkan.
    """
    payload = decode_token(token)
    user_id: int = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid: informasi pengguna tidak ditemukan.",
        )

    user = db.query(Pengguna).filter(Pengguna.id == int(user_id)).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun tidak ditemukan. Silakan login ulang.",
        )

    if not user.is_aktif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda telah dinonaktifkan. Hubungi Peneliti.",
        )

    return user


def require_role(*roles: str):
    """
    Dependency factory: batasi akses endpoint berdasarkan role.
    Contoh: Depends(require_role('admin', 'peneliti'))
    """
    def checker(user: Pengguna = Depends(get_current_user)) -> Pengguna:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Akses ditolak. Fitur ini hanya untuk: {', '.join(roles)}.",
            )
        return user
    return checker
