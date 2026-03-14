"""
ml/lp_optimizer.py — Optimisasi alokasi modal harian menggunakan Linear Programming.

Formulasi LP:
  Maksimalkan:  Σ x_i × margin_ratio_i
  Subjek ke:    Σ x_i ≤ modal_harian_rp          (kendala likuiditas)
                x_i ≥ min_modal_harian_i           (kendala minimum per produk)
                x_i ≥ 0

Implementasi: scipy.optimize.linprog (method='highs')
linprog meminimalkan, jadi objective dinegasikan.
"""
import sys
import os
import numpy as np
from scipy.optimize import linprog
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.models import Produk


# ─── HELPER ───────────────────────────────────────────────────────────────────

def hitung_estimasi_unit(alokasi_rp: float, harga_beli: float) -> float:
    """Estimasi unit yang bisa dibeli dari alokasi modal, dibulatkan 1 desimal."""
    if harga_beli <= 0:
        return 0.0
    return round(alokasi_rp / harga_beli, 1)


def hitung_estimasi_profit(alokasi_rp: float, margin_ratio: float) -> float:
    """Estimasi profit bersih dari alokasi modal dan margin ratio."""
    return round(alokasi_rp * margin_ratio, 2)


# ─── OPTIMASI LP ──────────────────────────────────────────────────────────────

def optimasi_alokasi(
    modal_harian_rp: float,
    prediksi_list: list[dict],
    db: Session,
) -> dict:
    """
    Hitung alokasi modal optimal menggunakan Linear Programming.

    Args:
      modal_harian_rp — total modal yang tersedia (Rp)
      prediksi_list   — list dict hasil prediksi_ensemble() per produk
                        (harus punya key: produk_id, margin_ratio)
      db              — SQLAlchemy Session

    Return dict kompatibel dengan AlokasiResponse:
      modal_total_rp, expected_net_profit_rp, status_lp, alokasi [...]
    """
    if not prediksi_list:
        raise ValueError("Daftar prediksi kosong. Jalankan prediksi terlebih dahulu.")

    n = len(prediksi_list)

    # ── Kumpulkan data per produk dari DB ─────────────────────────────────
    produk_ids   = [item["produk_id"] for item in prediksi_list]
    margin_ratios = np.array([item["margin_ratio"] for item in prediksi_list], dtype=float)

    produk_map: dict[int, Produk] = {
        p.id: p
        for p in db.query(Produk).filter(Produk.id.in_(produk_ids)).all()
    }

    min_modal = np.array([
        produk_map[pid].min_modal_harian if pid in produk_map else 0.0
        for pid in produk_ids
    ], dtype=float)

    harga_beli_map = {
        pid: produk_map[pid].harga_beli_per_unit
        for pid in produk_ids if pid in produk_map
    }

    # ── Validasi: modal mencukupi minimum semua produk ────────────────────
    total_minimum = float(min_modal.sum())
    if total_minimum > modal_harian_rp:
        raise ValueError(
            f"Modal Rp {modal_harian_rp:,.0f} tidak cukup untuk memenuhi alokasi minimum. "
            f"Total minimum semua produk adalah Rp {total_minimum:,.0f}. "
            f"Tambahkan modal minimal Rp {total_minimum - modal_harian_rp:,.0f} lagi."
        )

    # ── Formulasi LP ──────────────────────────────────────────────────────
    # linprog minimasi → negatifkan margin_ratio untuk maksimasi profit
    c = -margin_ratios

    # Kendala inequality: Σ x_i ≤ modal_harian_rp → A_ub @ x ≤ b_ub
    A_ub = np.ones((1, n))
    b_ub = np.array([modal_harian_rp])

    # Batas bawah: x_i ≥ min_modal_i, tidak ada batas atas (None)
    bounds = [(float(min_modal[i]), None) for i in range(n)]

    # ── Solve ─────────────────────────────────────────────────────────────
    hasil_lp = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=bounds,
        method="highs",
    )

    # ── Cek status solver ─────────────────────────────────────────────────
    if hasil_lp.status != 0:
        return {
            "modal_total_rp":        modal_harian_rp,
            "expected_net_profit_rp": 0.0,
            "status_lp":             "infeasible",
            "alokasi":               [],
            "pesan":                 (
                "Solver LP tidak menemukan solusi optimal. "
                "Coba kurangi jumlah produk aktif atau tambah modal harian."
            ),
            "proses_lp":             None,
        }

    alokasi_optimal = np.maximum(hasil_lp.x, min_modal)  # pastikan ≥ minimum
    expected_profit = float(np.dot(alokasi_optimal, margin_ratios))

    # ── Susun detail per produk ───────────────────────────────────────────
    alokasi_list = []
    for i, pid in enumerate(produk_ids):
        alokasi_rp  = float(alokasi_optimal[i])
        persen      = round(alokasi_rp / modal_harian_rp * 100, 2) if modal_harian_rp > 0 else 0.0
        harga_beli  = harga_beli_map.get(pid, 1.0)
        est_unit    = hitung_estimasi_unit(alokasi_rp, harga_beli)
        est_profit  = hitung_estimasi_profit(alokasi_rp, float(margin_ratios[i]))

        alokasi_list.append({
            "produk_id":        pid,
            "nama_produk":      prediksi_list[i]["nama_produk"],
            "alokasi_rp":       round(alokasi_rp, 2),
            "persentase":       persen,
            "estimasi_unit":    est_unit,
            "estimasi_profit_rp": round(est_profit, 2),
        })

    # Urutkan dari alokasi terbesar
    alokasi_list.sort(key=lambda x: x["alokasi_rp"], reverse=True)

    # Kumpulkan data proses LP untuk transparansi peneliti
    prediksi_list_sorted = prediksi_list  # alias (urutan asli, sesuai indeks x_opt)
    x_opt = alokasi_optimal

    proses_lp = {
        "n_variabel": n,
        "n_kendala": len(b_ub) + len(bounds),
        "solver": "HiGHS",
        "status_solver": hasil_lp.message,
        "n_iterasi": getattr(hasil_lp, "nit", 0),
        "fungsi_tujuan": "maks Σ xᵢ × marginᵢ",
        "margin_per_produk": [
            {
                "nama": p["nama_produk"],
                "margin_ratio": round(float(p["margin_ratio"]), 4),
                "alokasi_rp": round(float(x_opt[i]), 2),
                "terpilih": float(x_opt[i]) > float(min_modal[i]) * 1.001,
            }
            for i, p in enumerate(prediksi_list_sorted)
        ],
    }

    return {
        "modal_total_rp":         modal_harian_rp,
        "expected_net_profit_rp": round(expected_profit, 2),
        "status_lp":              "optimal",
        "alokasi":                alokasi_list,
        "proses_lp":              proses_lp,
    }
