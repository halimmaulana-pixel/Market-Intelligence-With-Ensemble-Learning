"""
jwt_handler.py — Buat dan decode JWT token untuk autentikasi SalSa Market.
"""
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SECRET_KEY, ALGORITHM, TOKEN_EXPIRE_HOURS


def create_access_token(data: dict) -> str:
    """
    Buat JWT access token dari payload data.
    Otomatis tambahkan exp (expiry) sesuai TOKEN_EXPIRE_HOURS di config.
    """
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode dan validasi JWT token.
    Raise HTTP 401 jika token tidak valid atau sudah expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kedaluwarsa. Silakan login ulang.",
            headers={"WWW-Authenticate": "Bearer"},
        )
