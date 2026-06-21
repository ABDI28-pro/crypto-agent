"""
test_tools.py — Test semua API gratis TANPA perlu Groq key.

Jalankan ini PERTAMA untuk pastikan CoinGecko bisa diakses.
Kalau semua OK baru isi GROQ_API_KEY di .env lalu jalankan agent.py

Cara jalankan:
    python test_tools.py
"""

import json
from tools import (
    get_crypto_price,
    get_market_overview,
    get_fear_and_greed,
    get_trending_coins,
    get_global_market_stats,
)


def cek(label: str, result: dict):
    """Print hasil test dengan format rapi."""
    if "error" in result:
        print(f"  GAGAL — {result['error']}")
    else:
        print(f"  OK")
        print(json.dumps(result, indent=4, ensure_ascii=False))
    print()


print("=" * 56)
print("  Test Semua API Gratis")
print("=" * 56)

print("\n[1/5] Harga Bitcoin...")
cek("BTC", get_crypto_price("bitcoin"))

print("[2/5] Harga Ethereum...")
cek("ETH", get_crypto_price("ethereum"))

print("[3/5] Market Overview (BTC/ETH/SOL/BNB)...")
cek("overview", get_market_overview())

print("[4/5] Fear & Greed Index...")
cek("fng", get_fear_and_greed())

print("[5/5] Trending Coins...")
result = get_trending_coins()
if "error" not in result:
    print("  OK")
    for c in result.get("trending", []):
        rank = c["market_cap_rank"]
        print(f"  #{rank:>4}  {c['symbol']:<8} {c['name']}")
else:
    print(f"  GAGAL — {result['error']}")
print()

print("[BONUS] Global Market Stats...")
cek("global", get_global_market_stats())

print("=" * 56)
print("  Kalau semua OK → isi GROQ_API_KEY di .env")
print("  Lalu jalankan: python agent.py")
print("=" * 56)
