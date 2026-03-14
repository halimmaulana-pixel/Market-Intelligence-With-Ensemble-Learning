"""
routers/histori.py — Histori penjualan harian per produk.
GET semua role login, POST hanya admin dan peneliti.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import List
import numpy as np

from database.db import get_db
from database.models import Produk, HistoriPenjualan
from schemas.histori import HistoriCreate, HistoriResponse
from auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/histori", tags=["Histori Penjualan"])

NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def _get_produk_or_404(produk_id: int, db: Session) -> Produk:
    produk = db.query(Produk).filter(Produk.id == produk_id).first()
    if not produk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produk dengan ID {produk_id} tidak ditemukan.",
        )
    return produk


def _to_response(row: HistoriPenjualan, nama_produk: str) -> dict:
    return {
        "id":            row.id,
        "produk_id":     row.produk_id,
        "nama_produk":   nama_produk,
        "tanggal":       row.tanggal,
        "penjualan_rp":  row.penjualan_rp,
        "penjualan_unit": row.penjualan_unit,
        "cuaca":         row.cuaca,
        "hari_besar":    row.hari_besar,
        "is_dummy":      row.is_dummy,
    }


# ── GET /api/histori/{produk_id} ──────────────────────────────────────────────

@router.get("/{produk_id}", summary="Histori penjualan per produk")
def get_histori(
    produk_id: int,
    limit: int = Query(90, ge=1, le=365, description="Jumlah hari terakhir (default 90, max 365)"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Kembalikan histori penjualan N hari terakhir untuk produk tertentu,
    diurutkan ascending by tanggal.
    """
    produk = _get_produk_or_404(produk_id, db)

    tanggal_mulai = date.today() - timedelta(days=limit)

    rows = (
        db.query(HistoriPenjualan)
        .filter(
            HistoriPenjualan.produk_id == produk_id,
            HistoriPenjualan.tanggal >= tanggal_mulai,
        )
        .order_by(HistoriPenjualan.tanggal.asc())
        .all()
    )

    return [_to_response(r, produk.nama_produk) for r in rows]


# ── GET /api/histori/{produk_id}/statistik ────────────────────────────────────

@router.get("/{produk_id}/statistik", summary="Statistik penjualan per produk")
def get_statistik(
    produk_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Kembalikan statistik deskriptif penjualan:
    mean, min, max, std, dan rata-rata per hari minggu.
    """
    produk = _get_produk_or_404(produk_id, db)

    rows = (
        db.query(HistoriPenjualan)
        .filter(HistoriPenjualan.produk_id == produk_id)
        .order_by(HistoriPenjualan.tanggal.asc())
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tidak ada data histori untuk produk '{produk.nama_produk}'.",
        )

    nilai = np.array([r.penjualan_rp for r in rows])

    # Rata-rata per hari minggu
    rata_hari = {}
    for i, nama_hari in enumerate(NAMA_HARI):
        y_hari = [r.penjualan_rp for r in rows
                  if isinstance(r.tanggal, date) and r.tanggal.weekday() == i]
        rata_hari[nama_hari] = round(float(np.mean(y_hari)), 0) if y_hari else 0.0

    return {
        "produk_id":   produk_id,
        "nama_produk": produk.nama_produk,
        "n_observasi": len(rows),
        "tanggal_awal": rows[0].tanggal,
        "tanggal_akhir": rows[-1].tanggal,
        "mean_rp":  round(float(np.mean(nilai)), 0),
        "min_rp":   round(float(np.min(nilai)), 0),
        "max_rp":   round(float(np.max(nilai)), 0),
        "std_rp":   round(float(np.std(nilai, ddof=1)), 0),
        "rata_per_hari": rata_hari,
    }


# ── POST /api/histori/{produk_id} ─────────────────────────────────────────────

@router.post("/{produk_id}", status_code=status.HTTP_201_CREATED,
             summary="Tambah entri histori manual")
def tambah_histori(
    produk_id: int,
    body: HistoriCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin", "peneliti")),
):
    """
    Tambah satu entri penjualan manual (is_dummy=False).
    Cegah duplikat tanggal untuk produk yang sama.
    """
    produk = _get_produk_or_404(produk_id, db)

    # Cek duplikat tanggal
    existing = db.query(HistoriPenjualan).filter(
        HistoriPenjualan.produk_id == produk_id,
        HistoriPenjualan.tanggal == body.tanggal,
        HistoriPenjualan.is_dummy == False,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Data penjualan '{produk.nama_produk}' untuk tanggal "
                f"{body.tanggal.strftime('%d %B %Y')} sudah ada."
            ),
        )

    entri = HistoriPenjualan(
        produk_id=produk_id,
        tanggal=body.tanggal,
        penjualan_rp=body.penjualan_rp,
        penjualan_unit=body.penjualan_unit,
        cuaca=body.cuaca,
        hari_besar=body.hari_besar,
        is_dummy=False,
    )
    db.add(entri)
    db.commit()
    db.refresh(entri)

    return _to_response(entri, produk.nama_produk)
