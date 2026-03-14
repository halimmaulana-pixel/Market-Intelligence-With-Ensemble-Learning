"""
routers/produk.py — CRUD produk dan harga.
GET semua role login, POST/PUT/DELETE hanya admin dan peneliti.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from database.db import get_db
from database.models import Produk, ModelConfig
from schemas.produk import ProdukCreate, ProdukUpdate, ProdukResponse
from auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/produk", tags=["Produk"])


def _get_produk_or_404(produk_id: int, db: Session) -> Produk:
    produk = db.query(Produk).filter(Produk.id == produk_id).first()
    if not produk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produk dengan ID {produk_id} tidak ditemukan.",
        )
    return produk


# ── GET /api/produk ───────────────────────────────────────────────────────────

@router.get("", response_model=List[ProdukResponse], summary="Daftar semua produk aktif")
def list_produk(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Kembalikan semua produk yang is_aktif=True."""
    return db.query(Produk).filter(Produk.is_aktif == True).order_by(Produk.id).all()


# ── GET /api/produk/{id} ──────────────────────────────────────────────────────

@router.get("/{produk_id}", response_model=ProdukResponse, summary="Detail satu produk")
def detail_produk(
    produk_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Kembalikan detail produk berdasarkan ID (aktif maupun nonaktif)."""
    return _get_produk_or_404(produk_id, db)


# ── POST /api/produk ──────────────────────────────────────────────────────────

@router.post("", response_model=ProdukResponse, status_code=status.HTTP_201_CREATED,
             summary="Tambah produk baru")
def tambah_produk(
    body: ProdukCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "peneliti")),
):
    """
    Tambah produk baru. Otomatis membuat ModelConfig default untuk produk ini.
    Validasi: harga_jual harus lebih besar dari harga_beli.
    """
    # Validasi harga
    if body.harga_jual_per_unit <= body.harga_beli_per_unit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Harga jual harus lebih besar dari harga beli.",
        )

    # Cek nama produk tidak duplikat
    existing = db.query(Produk).filter(Produk.nama_produk == body.nama_produk).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Produk dengan nama '{body.nama_produk}' sudah ada.",
        )

    produk = Produk(**body.model_dump())
    db.add(produk)
    db.flush()  # dapatkan produk.id

    # Buat ModelConfig default untuk produk baru
    config = ModelConfig(produk_id=produk.id)
    db.add(config)
    db.commit()
    db.refresh(produk)
    return produk


# ── PUT /api/produk/{id} ──────────────────────────────────────────────────────

@router.put("/{produk_id}", response_model=ProdukResponse, summary="Update produk atau harga")
def update_produk(
    produk_id: int,
    body: ProdukUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "peneliti")),
):
    """
    Update data produk atau harga beli/jual.
    Hanya field yang dikirim yang diupdate (partial update).
    """
    produk = _get_produk_or_404(produk_id, db)

    data = body.model_dump(exclude_unset=True)

    # Validasi harga jika keduanya dikirim
    harga_beli = data.get("harga_beli_per_unit", produk.harga_beli_per_unit)
    harga_jual = data.get("harga_jual_per_unit", produk.harga_jual_per_unit)
    if harga_jual <= harga_beli:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Harga jual harus lebih besar dari harga beli.",
        )

    for field, value in data.items():
        setattr(produk, field, value)
    produk.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(produk)
    return produk


# ── DELETE /api/produk/{id} ───────────────────────────────────────────────────

@router.delete("/{produk_id}", summary="Nonaktifkan produk (soft delete)")
def hapus_produk(
    produk_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "peneliti")),
):
    """
    Soft delete: set is_aktif=False. Data histori dan model tetap ada di DB.
    Produk tidak bisa dihapus permanen untuk menjaga integritas data histori.
    """
    produk = _get_produk_or_404(produk_id, db)

    if not produk.is_aktif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Produk '{produk.nama_produk}' sudah dalam keadaan nonaktif.",
        )

    produk.is_aktif = False
    produk.updated_at = datetime.utcnow()
    db.commit()

    return {"pesan": f"Produk '{produk.nama_produk}' berhasil dinonaktifkan."}
