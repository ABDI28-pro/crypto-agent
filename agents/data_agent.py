"""
agents/data_agent.py — Data Agent.

Tanggung jawab TUNGGAL: fetch data mentah dari semua sumber.
Tidak melakukan analisis apapun — murni pengumpul data.

Ini prinsip multi-agent: setiap agent punya 1 tanggung jawab jelas,
supaya mudah di-debug, di-test, dan di-upgrade secara independen.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import get_crypto_price, get_fear_and_greed, get_market_overview
from scalping_engine import fetch_ohlcv, calc_all_indicators
from support_resistance import get_support_resistance
from multi_timeframe import analyze_multi_timeframe


class DataAgent:
    """Agent yang bertugas mengumpulkan semua data mentah yang dibutuhkan."""

    name = "DataAgent"

    def gather(self, coin: str) -> dict:
        """
        Kumpulkan semua data mentah untuk satu koin.
        Return dict berisi: price, indicators, support/resistance, multi-timeframe, fear&greed
        """
        print(f"  [{self.name}] Mengumpulkan data untuk {coin.upper()}...")

        price_data = get_crypto_price(coin)
        if "error" in price_data:
            return {"error": price_data["error"], "agent": self.name}

        fg_data = get_fear_and_greed()
        fg_value = fg_data.get("value") if "error" not in fg_data else None

        df = fetch_ohlcv(coin, days=14)
        indicators = calc_all_indicators(df) if not df.empty else {}

        sr_levels = {}
        if not df.empty and indicators:
            sr_levels = get_support_resistance(df, indicators.get("price", price_data["price_usd"]))

        mtf_data = {}
        try:
            mtf_data = analyze_multi_timeframe(coin)
        except Exception as e:
            print(f"  [{self.name}] Multi-timeframe gagal: {e}")

        return {
            "agent": self.name,
            "coin": coin,
            "price_data": price_data,
            "indicators": indicators,
            "support_resistance": sr_levels,
            "multi_timeframe": mtf_data,
            "fear_greed": fg_value,
            "fear_greed_label": fg_data.get("label", "") if "error" not in fg_data else "",
        }

    def gather_market_snapshot(self, coins: list) -> dict:
        """Kumpulkan snapshot market untuk beberapa koin sekaligus (lebih ringan)."""
        print(f"  [{self.name}] Mengumpulkan market snapshot ({len(coins)} koin)...")
        overview = get_market_overview(coins)
        fg_data = get_fear_and_greed()
        return {
            "agent": self.name,
            "market": overview,
            "fear_greed": fg_data.get("value") if "error" not in fg_data else None,
        }
