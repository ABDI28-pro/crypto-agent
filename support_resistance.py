"""
support_resistance.py — Deteksi level support & resistance otomatis.

Metode: Swing High/Low detection + price clustering.
Level S/R dipakai untuk menentukan entry, TP, dan SL yang
secara teknikal masuk akal — bukan cuma jarak ATR sembarangan.
"""

import pandas as pd
import numpy as np


def find_swing_points(df: pd.DataFrame, window: int = 5) -> dict:
    """
    Cari swing high dan swing low dari data harga.
    Swing high = titik tertinggi lokal (lebih tinggi dari N candle kiri-kanan)
    Swing low  = titik terendah lokal
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    swing_highs = []
    swing_lows = []

    for i in range(window, n - window):
        # Swing high: lebih tinggi dari semua tetangga dalam window
        if highs[i] == max(highs[i-window:i+window+1]):
            swing_highs.append(highs[i])
        # Swing low: lebih rendah dari semua tetangga dalam window
        if lows[i] == min(lows[i-window:i+window+1]):
            swing_lows.append(lows[i])

    return {"swing_highs": swing_highs, "swing_lows": swing_lows}


def cluster_levels(prices: list, tolerance_pct: float = 0.5) -> list:
    """
    Gabungkan harga-harga yang berdekatan jadi satu "level" S/R.
    Level yang muncul berkali-kali (banyak swing point berdekatan) = level kuat.
    """
    if not prices:
        return []

    sorted_prices = sorted(prices)
    clusters = []
    current_cluster = [sorted_prices[0]]

    for price in sorted_prices[1:]:
        if (price - current_cluster[-1]) / current_cluster[-1] * 100 <= tolerance_pct:
            current_cluster.append(price)
        else:
            clusters.append(current_cluster)
            current_cluster = [price]
    clusters.append(current_cluster)

    # Setiap cluster jadi 1 level, dengan strength = jumlah titik di cluster
    levels = []
    for cluster in clusters:
        levels.append({
            "price": round(sum(cluster) / len(cluster), 6),
            "strength": len(cluster),  # makin banyak titik, makin kuat levelnya
        })

    return sorted(levels, key=lambda x: x["strength"], reverse=True)


def get_support_resistance(df: pd.DataFrame, current_price: float, window: int = 5) -> dict:
    """
    Hitung level support dan resistance terdekat dari harga saat ini.

    Returns:
        {
            "nearest_support": float,
            "nearest_resistance": float,
            "support_strength": int,
            "resistance_strength": int,
            "all_supports": [...],
            "all_resistances": [...],
        }
    """
    if df.empty or len(df) < window * 3:
        return {}

    swings = find_swing_points(df, window)
    resistance_levels = cluster_levels(swings["swing_highs"])
    support_levels = cluster_levels(swings["swing_lows"])

    # Filter: support harus di bawah harga sekarang, resistance di atas
    supports_below = [lv for lv in support_levels if lv["price"] < current_price]
    resistances_above = [lv for lv in resistance_levels if lv["price"] > current_price]

    # Sort by jarak terdekat ke harga sekarang
    supports_below.sort(key=lambda x: current_price - x["price"])
    resistances_above.sort(key=lambda x: x["price"] - current_price)

    nearest_support = supports_below[0] if supports_below else None
    nearest_resistance = resistances_above[0] if resistances_above else None

    return {
        "nearest_support": nearest_support["price"] if nearest_support else None,
        "support_strength": nearest_support["strength"] if nearest_support else 0,
        "nearest_resistance": nearest_resistance["price"] if nearest_resistance else None,
        "resistance_strength": nearest_resistance["strength"] if nearest_resistance else 0,
        "all_supports": supports_below[:3],
        "all_resistances": resistances_above[:3],
    }
