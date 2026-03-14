"""
routers/prediksi.py — Endpoint prediksi ensemble SVR+SARIMA.
Akses: semua role yang sudah login.
"""
import time
from datetime import date
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Produk, ModelConfig
from schemas.prediksi import (
    PrediksiRequest, PrediksiResponse, PrediksiItemResponse,
    ProsesDetailResponse, VerbosePrediksiResponse,
)
from auth.dependencies import get_current_user, require_role
from ml.ensemble import prediksi_semua_produk, perlu_update_bobot, update_bobot_db
from ml.verbose import buat_proses_detail

router = APIRouter(prefix="/api/prediksi", tags=["Prediksi"])

TIMEOUT_DETIK = 30  # batas waktu prediksi


def _cek_model_tersedia(produk_ids: Optional[List[int]], db: Session) -> list[str]:
    """
    Cek apakah semua produk yang diminta sudah punya model terlatih.
    Return list nama produk yang belum dilatih (kosong = semua siap).
    """
    query = db.query(Produk, ModelConfig).outerjoin(
        ModelConfig, Produk.id == ModelConfig.produk_id
    ).filter(Produk.is_aktif == True)

    if produk_ids:
        query = query.filter(Produk.id.in_(produk_ids))

    belum_siap = []
    for produk, config in query.all():
        if config is None or not config.model_tersedia:
            belum_siap.append(produk.nama_produk)

    return belum_siap


def _jalankan_prediksi(request: PrediksiRequest, db: Session) -> dict:
    """Jalankan prediksi ensemble — dipanggil dalam thread untuk timeout support."""
    mulai = time.time()

    # Update bobot per produk yang perlu diperbarui
    query = db.query(ModelConfig).filter(ModelConfig.model_tersedia == True)
    if request.produk_ids:
        query = query.filter(ModelConfig.produk_id.in_(request.produk_ids))

    for config in query.all():
        if perlu_update_bobot(config.produk_id, db):
            update_bobot_db(config.produk_id, db)

    # Jalankan prediksi semua produk
    hasil = prediksi_semua_produk(
        tanggal=request.tanggal,
        cuaca=request.cuaca.value,
        hari_besar=request.hari_besar,
        produk_ids=request.produk_ids,
        db=db,
    )

    durasi = time.time() - mulai
    n = len(hasil["prediksi"])
    print(f"[PREDIKSI] selesai dalam {durasi:.2f}s untuk {n} produk")
    return hasil


# ── GET /api/prediksi/status ──────────────────────────────────────────────────

@router.get("/status", summary="Status kesiapan model semua produk")
def status_model(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Kembalikan berapa produk sudah siap (model_tersedia=True) vs belum,
    beserta daftar nama produk yang belum dilatih.
    """
    rows = db.query(Produk, ModelConfig).outerjoin(
        ModelConfig, Produk.id == ModelConfig.produk_id
    ).filter(Produk.is_aktif == True).all()

    siap = []
    belum_siap = []
    for produk, config in rows:
        if config and config.model_tersedia:
            siap.append({
                "produk_id":    produk.id,
                "nama_produk":  produk.nama_produk,
                "last_trained": config.last_trained,
                "mape_svr":     config.mape_svr,
                "mape_sarima":  config.mape_sarima,
            })
        else:
            belum_siap.append({
                "produk_id":   produk.id,
                "nama_produk": produk.nama_produk,
            })

    return {
        "total_produk":     len(rows),
        "siap":             len(siap),
        "belum_dilatih":    len(belum_siap),
        "produk_siap":      siap,
        "produk_belum_siap": belum_siap,
        "semua_siap":       len(belum_siap) == 0,
    }


# ── POST /api/prediksi/verbose ────────────────────────────────────────────────

@router.post(
    "/verbose",
    response_model=VerbosePrediksiResponse,
    summary="Prediksi verbose dengan transparansi proses ML (hanya Peneliti)",
)
def prediksi_verbose_endpoint(
    request: PrediksiRequest,
    db: Session = Depends(get_db),
    _=Depends(require_role("peneliti")),
):
    """
    Prediksi permintaan harian dengan detail transparansi proses ML per produk.
    Mencakup 5 tahap: Feature Engineering, SVR, SARIMA, Ensemble, dan Keuangan.
    Hanya dapat diakses oleh role Peneliti.
    """
    # ── Validasi produk_ids ────────────────────────────────────────────────
    if request.produk_ids:
        id_valid = {
            row.id for row in
            db.query(Produk.id).filter(Produk.id.in_(request.produk_ids)).all()
        }
        id_tidak_ada = [pid for pid in request.produk_ids if pid not in id_valid]
        if id_tidak_ada:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Produk dengan ID berikut tidak ditemukan: {id_tidak_ada}.",
            )

    # ── Validasi model tersedia ────────────────────────────────────────────
    belum_siap = _cek_model_tersedia(request.produk_ids, db)
    if belum_siap:
        total = len(request.produk_ids) if request.produk_ids else \
                db.query(Produk).filter(Produk.is_aktif == True).count()
        if len(belum_siap) == total:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model belum dilatih. Silakan hubungi Peneliti untuk menjalankan training.",
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Model belum tersedia untuk produk berikut: "
                f"{', '.join(belum_siap)}. "
                "Hubungi Peneliti untuk melatih model produk tersebut."
            ),
        )

    # ── Jalankan prediksi ensemble normal ─────────────────────────────────
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_jalankan_prediksi, request, db)
        try:
            hasil = future.result(timeout=TIMEOUT_DETIK)
        except FuturesTimeout:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    f"Prediksi memakan waktu lebih dari {TIMEOUT_DETIK} detik dan dihentikan. "
                    "Coba kurangi jumlah produk atau hubungi Peneliti."
                ),
            )

    if not hasil["prediksi"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediksi gagal untuk semua produk. Pastikan model sudah dilatih.",
        )

    # ── Susun proses_detail per produk ────────────────────────────────────
    proses_detail = []
    for item in hasil["prediksi"]:
        produk_id = item["produk_id"]
        try:
            detail = buat_proses_detail(
                produk_id=produk_id,
                tanggal=request.tanggal,
                cuaca=request.cuaca.value,
                hari_besar=request.hari_besar,
                db=db,
            )
            proses_detail.append(detail)
        except Exception as e:
            print(f"[VERBOSE] WARNING produk_id={produk_id} — {e}")
            proses_detail.append({
                "produk_id": produk_id,
                "nama_produk": item.get("nama_produk", f"Produk #{produk_id}"),
                "tahap_1_fitur": {"error": str(e)},
                "tahap_2_svr": {},
                "tahap_3_sarima": {},
                "tahap_4_ensemble": {},
                "tahap_5_keuangan": {},
            })

    return {
        "tanggal": hasil["tanggal"],
        "prediksi": hasil["prediksi"],
        "proses_detail": proses_detail,
    }


# ── POST /api/prediksi ────────────────────────────────────────────────────────

@router.post("", response_model=PrediksiResponse, summary="Prediksi permintaan harian")
def prediksi(
    request: PrediksiRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """
    Prediksi permintaan harian menggunakan ensemble SVR+SARIMA.
    Semua model harus sudah dilatih sebelum prediksi bisa dijalankan.
    Bobot ensemble diperbarui otomatis jika sudah > 7 hari.
    """
    # ── Validasi: produk_ids yang diminta harus ada di DB ─────────────────
    if request.produk_ids:
        id_valid = {
            row.id for row in
            db.query(Produk.id).filter(Produk.id.in_(request.produk_ids)).all()
        }
        id_tidak_ada = [pid for pid in request.produk_ids if pid not in id_valid]
        if id_tidak_ada:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Produk dengan ID berikut tidak ditemukan: {id_tidak_ada}.",
            )

    # ── Validasi: semua model harus sudah dilatih ──────────────────────────
    belum_siap = _cek_model_tersedia(request.produk_ids, db)

    if belum_siap:
        # Jika SEMUA produk belum dilatih → 503
        total = len(request.produk_ids) if request.produk_ids else \
                db.query(Produk).filter(Produk.is_aktif == True).count()
        if len(belum_siap) == total:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model belum dilatih. Silakan hubungi Peneliti untuk menjalankan training.",
            )
        # Sebagian belum → 422 dengan nama produk
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Model belum tersedia untuk produk berikut: "
                f"{', '.join(belum_siap)}. "
                "Hubungi Peneliti untuk melatih model produk tersebut."
            ),
        )

    # ── Jalankan prediksi dengan timeout 30 detik ─────────────────────────
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_jalankan_prediksi, request, db)
        try:
            hasil = future.result(timeout=TIMEOUT_DETIK)
        except FuturesTimeout:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    f"Prediksi memakan waktu lebih dari {TIMEOUT_DETIK} detik dan dihentikan. "
                    "Coba kurangi jumlah produk atau hubungi Peneliti."
                ),
            )

    if not hasil["prediksi"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prediksi gagal untuk semua produk. Pastikan model sudah dilatih.",
        )

    return hasil
