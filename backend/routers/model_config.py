"""
routers/model_config.py — Konfigurasi parameter ML dan trigger training.
GET semua role login, PUT/POST training hanya peneliti.
"""
import time
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Produk, ModelConfig
from schemas.model_config import ModelConfigResponse, ModelConfigUpdate, TrainingResponse
from auth.dependencies import get_current_user, require_role
from ml.svr_model import latih_svr
from ml.sarima_model import latih_sarima
from ml.evaluator import evaluasi_semua_model, evaluasi_semua_produk

router = APIRouter(prefix="/api/model-config", tags=["Model Config"])

TRAINING_TIMEOUT = 600  # 10 menit


def _get_config_or_404(produk_id: int, db: Session) -> ModelConfig:
    config = db.query(ModelConfig).filter(ModelConfig.produk_id == produk_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Konfigurasi model untuk produk ID {produk_id} tidak ditemukan.",
        )
    return config


def _enrich(config: ModelConfig, db: Session) -> dict:
    """Tambahkan nama_produk ke ModelConfig untuk response."""
    produk = db.query(Produk).filter(Produk.id == config.produk_id).first()
    nama = produk.nama_produk if produk else "—"
    d = {c.name: getattr(config, c.name) for c in config.__table__.columns}
    d["nama_produk"] = nama
    return d


def _latih_satu_produk(produk_id: int, user_id: int, db: Session) -> dict:
    """Latih SVR + SARIMA untuk satu produk, return ringkasan."""
    hasil_svr = latih_svr(produk_id, db, user_id)
    hasil_sarima = latih_sarima(produk_id, db, user_id)
    return {"produk_id": produk_id, "svr": hasil_svr, "sarima": hasil_sarima}


# ── GET /api/model-config ─────────────────────────────────────────────────────

@router.get("", response_model=List[ModelConfigResponse], summary="Daftar konfigurasi model semua produk")
def list_model_config(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Kembalikan konfigurasi ML untuk semua produk aktif."""
    rows = (
        db.query(ModelConfig, Produk)
        .join(Produk, ModelConfig.produk_id == Produk.id)
        .filter(Produk.is_aktif == True)
        .order_by(ModelConfig.produk_id)
        .all()
    )
    hasil = []
    for config, produk in rows:
        d = {c.name: getattr(config, c.name) for c in config.__table__.columns}
        d["nama_produk"] = produk.nama_produk
        hasil.append(d)
    return hasil


# ── GET /api/model-config/{produk_id} ────────────────────────────────────────

@router.get("/{produk_id}", response_model=ModelConfigResponse, summary="Konfigurasi model satu produk")
def detail_model_config(
    produk_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    config = _get_config_or_404(produk_id, db)
    return _enrich(config, db)


# ── PUT /api/model-config/{produk_id} ────────────────────────────────────────

@router.put("/{produk_id}", response_model=ModelConfigResponse, summary="Update parameter model (hanya Peneliti)")
def update_model_config(
    produk_id: int,
    body: ModelConfigUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("peneliti")),
):
    """
    Update parameter SVR dan SARIMA secara manual.
    Jika `auto_tune=True`, parameter ini akan diabaikan saat training dan
    digantikan oleh hasil GridSearch/auto_arima.
    """
    config = _get_config_or_404(produk_id, db)

    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return _enrich(config, db)


# ── POST /api/model-config/training/all ───────────────────────────────────────

@router.post(
    "/training/all",
    response_model=TrainingResponse,
    summary="Latih ulang SEMUA model (hanya Peneliti)",
)
def training_semua(
    db: Session = Depends(get_db),
    user=Depends(require_role("peneliti")),
):
    """
    Latih SVR + SARIMA untuk semua produk aktif yang punya ModelConfig.
    Proses berjalan sinkron (blokir) — bisa memakan waktu beberapa menit.
    """
    produk_list = (
        db.query(Produk).filter(Produk.is_aktif == True).order_by(Produk.id).all()
    )
    if not produk_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tidak ada produk aktif yang bisa dilatih.",
        )

    mulai = time.time()
    berhasil = 0
    gagal = []

    for produk in produk_list:
        try:
            latih_svr(produk.id, db, user.id)
            latih_sarima(produk.id, db, user.id)
            berhasil += 1
            print(f"[TRAINING] produk_id={produk.id} ({produk.nama_produk}) — selesai")
        except Exception as e:
            gagal.append(produk.nama_produk)
            print(f"[TRAINING] produk_id={produk.id} gagal: {e}")

    durasi = round(time.time() - mulai, 2)

    if berhasil == 0:
        return TrainingResponse(
            status="gagal",
            pesan=f"Semua produk gagal dilatih: {', '.join(gagal)}.",
            produk_dilatih=0,
            durasi_detik=durasi,
        )

    pesan = f"Model berhasil dilatih untuk {berhasil} produk."
    if gagal:
        pesan += f" Gagal: {', '.join(gagal)}."

    return TrainingResponse(
        status="berhasil" if not gagal else "sebagian",
        pesan=pesan,
        produk_dilatih=berhasil,
        durasi_detik=durasi,
    )


# ── POST /api/model-config/training/{produk_id} ───────────────────────────────

@router.post(
    "/training/{produk_id}",
    response_model=TrainingResponse,
    summary="Latih ulang model satu produk (hanya Peneliti)",
)
def training_satu(
    produk_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("peneliti")),
):
    """
    Latih SVR + SARIMA untuk produk tertentu.
    Bersifat sinkron — tunggu hingga selesai.
    """
    # Pastikan produk dan config ada
    produk = db.query(Produk).filter(Produk.id == produk_id).first()
    if not produk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produk dengan ID {produk_id} tidak ditemukan.",
        )
    _get_config_or_404(produk_id, db)

    mulai = time.time()
    try:
        latih_svr(produk_id, db, user.id)
        latih_sarima(produk_id, db, user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training gagal untuk '{produk.nama_produk}': {str(e)}",
        )

    durasi = round(time.time() - mulai, 2)
    return TrainingResponse(
        status="berhasil",
        pesan=f"Model SVR dan SARIMA untuk '{produk.nama_produk}' berhasil dilatih.",
        produk_dilatih=1,
        durasi_detik=durasi,
    )


# ── GET /api/model-config/evaluasi/all ───────────────────────────────────────

@router.get("/evaluasi/all", summary="Evaluasi performa model semua produk (hanya Peneliti)")
def evaluasi_all(
    db: Session = Depends(get_db),
    _=Depends(require_role("peneliti")),
):
    """Kembalikan metrik evaluasi (MAPE, RMSE, MAE, R²) untuk semua produk terlatih."""
    return evaluasi_semua_produk(db)


# ── GET /api/model-config/evaluasi/{produk_id} ───────────────────────────────

@router.get("/evaluasi/{produk_id}", summary="Evaluasi performa model satu produk (hanya Peneliti)")
def evaluasi_satu(
    produk_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("peneliti")),
):
    """Kembalikan metrik evaluasi detail untuk satu produk."""
    config = _get_config_or_404(produk_id, db)
    if not config.model_tersedia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model untuk produk ID {produk_id} belum dilatih.",
        )
    return evaluasi_semua_model(produk_id, db)
