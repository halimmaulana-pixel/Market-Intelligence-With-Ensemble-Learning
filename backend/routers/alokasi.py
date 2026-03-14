"""
routers/alokasi.py — Endpoint optimisasi alokasi modal harian (Linear Programming).
Akses: semua role yang sudah login.
"""
import time
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Produk, ModelConfig
from schemas.alokasi import AlokasiRequest, AlokasiResponse
from auth.dependencies import get_current_user
from ml.ensemble import prediksi_semua_produk, perlu_update_bobot, update_bobot_db
from ml.lp_optimizer import optimasi_alokasi

router = APIRouter(prefix="/api/alokasi-modal", tags=["Alokasi Modal"])


def _pastikan_semua_model_siap(db: Session):
    """Raise HTTP 503 jika tidak ada satupun produk dengan model terlatih."""
    ada_model = db.query(ModelConfig).filter(ModelConfig.model_tersedia == True).first()
    if not ada_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model belum dilatih. Silakan hubungi Peneliti untuk menjalankan training.",
        )


def _dapatkan_prediksi(tanggal: date, db: Session) -> list[dict]:
    """
    Ambil prediksi untuk tanggal tertentu.
    Otomatis jalankan prediksi jika belum ada (auto-prediksi).
    Hanya menyertakan produk yang model_tersedia=True.
    """
    # Update bobot yang kedaluwarsa terlebih dahulu
    for config in db.query(ModelConfig).filter(ModelConfig.model_tersedia == True).all():
        if perlu_update_bobot(config.produk_id, db):
            update_bobot_db(config.produk_id, db)

    # Jalankan prediksi ensemble untuk produk yang siap
    produk_siap = [
        c.produk_id for c in
        db.query(ModelConfig).filter(ModelConfig.model_tersedia == True).all()
    ]

    if not produk_siap:
        return []

    hasil = prediksi_semua_produk(
        tanggal=tanggal,
        cuaca="cerah",       # default cuaca untuk alokasi (bisa dikembangkan)
        hari_besar=None,
        produk_ids=produk_siap,
        db=db,
    )
    return hasil["prediksi"]


def _jalankan_alokasi(modal: float, tanggal: date, db: Session) -> dict:
    """Inti alokasi: dapatkan prediksi lalu optimasi LP."""
    _pastikan_semua_model_siap(db)

    mulai = time.time()
    prediksi_list = _dapatkan_prediksi(tanggal, db)

    if not prediksi_list:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tidak ada model yang siap untuk membuat prediksi.",
        )

    try:
        hasil_lp = optimasi_alokasi(modal, prediksi_list, db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    durasi = time.time() - mulai
    print(f"[ALOKASI] LP selesai dalam {durasi:.2f}s — modal Rp {modal:,.0f} → {hasil_lp['status_lp']}")
    return hasil_lp


# ── POST /api/alokasi-modal ───────────────────────────────────────────────────

@router.post("", response_model=AlokasiResponse, summary="Optimasi alokasi modal harian")
def alokasi_modal(
    request: AlokasiRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Hitung alokasi modal optimal menggunakan Linear Programming.
    Prediksi dijalankan otomatis jika belum tersedia untuk tanggal yang diminta.
    Modal minimum: Rp 50.000.
    """
    # Double-check validasi modal (sudah di schema, ini lapisan pengaman kedua)
    if request.modal_harian_rp < 50_000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Modal harian minimal Rp 50.000.",
        )

    return _jalankan_alokasi(request.modal_harian_rp, request.prediksi_tanggal, db)


# ── GET /api/alokasi-modal/simulasi ──────────────────────────────────────────

@router.get("/simulasi", response_model=AlokasiResponse, summary="Simulasi alokasi modal cepat")
def simulasi_alokasi(
    modal: float = Query(..., ge=50_000, description="Modal yang ingin disimulasikan (Rp)"),
    tanggal: Optional[date] = Query(None, description="Tanggal simulasi (default: hari ini)"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Simulasi cepat alokasi modal tanpa menyimpan apapun ke database.
    Berguna untuk fitur slider modal di frontend.
    Tanggal default: hari ini.
    """
    tgl = tanggal or date.today()
    return _jalankan_alokasi(modal, tgl, db)
