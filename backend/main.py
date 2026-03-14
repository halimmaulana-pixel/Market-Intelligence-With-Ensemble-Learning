"""
main.py — Entry point aplikasi FastAPI SalSa Market Intelligence System.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routers import auth, produk, histori, prediksi, alokasi, model_config, pengguna

app = FastAPI(
    title="SalSa Market Intelligence System",
    description="Sistem Prediksi Permintaan & Optimisasi Alokasi Modal untuk UMKM Pasar Tradisional Kota Medan",
    version="1.0.0",
)

# CORS — izinkan frontend Vite (localhost:5173) dan localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Daftarkan semua router
app.include_router(auth.router)
app.include_router(produk.router)
app.include_router(histori.router)
app.include_router(prediksi.router)
app.include_router(alokasi.router)
app.include_router(model_config.router)
app.include_router(pengguna.router)


@app.get("/", tags=["Root"])
def root():
    return {"pesan": "SalSa Market Intelligence System berjalan. Akses /docs untuk dokumentasi API."}
