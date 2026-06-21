"""
live_ticker.py — Live price ticker di terminal, update terus menerus.

Cara jalankan:
  python live_ticker.py                          → default: BTC, ETH, SOL, BNB, XRP
  python live_ticker.py --coins btc eth doge      → koin pilihan
  python live_ticker.py --interval 5              → update tiap 5 detik (default 10)
  python live_ticker.py --scalp                   → tampilkan juga sinyal scalping

Tekan Ctrl+C untuk berhenti.
"""

import time
import argparse
import os
import sys
from datetime import datetime
from tools import get_market_overview, get_fear_and_greed

DEFAULT_COINS = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple"]

# Simpan harga sebelumnya untuk hitung arah pergerakan real-time (vs refresh terakhir)
_last_prices = {}


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def colorize(text: str, color: str) -> str:
    """ANSI color codes — bekerja di Windows Terminal, VS Code terminal, PowerShell modern."""
    codes = {
        "green": "\033[92m", "red": "\033[91m",
        "yellow": "\033[93m", "cyan": "\033[96m",
        "white": "\033[97m", "gray": "\033[90m",
        "bold": "\033[1m", "reset": "\033[0m",
    }
    return f"{codes.get(color, '')}{text}{codes['reset']}"


def format_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:,.4f}"
    else:
        return f"${price:,.6f}"


def render_ticker(coins: list, fg_val: int = None, fg_label: str = "", tick_count: int = 0):
    """Render satu frame ticker ke terminal."""
    clear_screen()

    now = datetime.now().strftime("%H:%M:%S")
    print(colorize("=" * 64, "cyan"))
    print(colorize(f"  LIVE CRYPTO TICKER", "bold") + colorize(f"   {now}   (update #{tick_count})", "gray"))
    print(colorize("=" * 64, "cyan"))

    if fg_val is not None:
        fg_color = "red" if fg_val >= 65 else "green" if fg_val <= 35 else "yellow"
        print(f"  Fear & Greed: {colorize(str(fg_val), fg_color)}/100 ({fg_label})")
        print(colorize("-" * 64, "gray"))

    print(f"  {'Coin':<14}{'Price':>16}{'24h %':>12}{'Tick':>8}")
    print(colorize("-" * 64, "gray"))

    market = get_market_overview(coins)

    if "error" in market:
        print(colorize(f"  Error: {market['error']}", "red"))
        return

    for coin_id, data in market.items():
        price = data["price_usd"]
        change = data["change_24h_pct"]

        # Bandingkan dengan harga tick sebelumnya (real-time micro-movement)
        prev = _last_prices.get(coin_id)
        if prev is None:
            tick_arrow = colorize("●", "gray")
        elif price > prev:
            tick_arrow = colorize("▲", "green")
        elif price < prev:
            tick_arrow = colorize("▼", "red")
        else:
            tick_arrow = colorize("●", "gray")
        _last_prices[coin_id] = price

        change_color = "green" if change >= 0 else "red"
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"

        name = coin_id.replace("-", " ").title()[:13]
        price_str = format_price(price)

        print(f"  {name:<14}{price_str:>16}{colorize(change_str, change_color):>21}{tick_arrow:>9}")

    print(colorize("-" * 64, "gray"))
    print(colorize("  Ctrl+C untuk berhenti", "gray"))


def run_ticker(coins: list, interval: int = 10):
    """Loop utama — update terus sampai Ctrl+C."""
    tick_count = 0
    fg_val, fg_label = None, ""
    fg_check_interval = 6  # cek Fear & Greed tiap 6 tick (jarang berubah)

    print("Memulai live ticker...")
    time.sleep(1)

    try:
        while True:
            tick_count += 1

            if tick_count == 1 or tick_count % fg_check_interval == 0:
                fg_data = get_fear_and_greed()
                if "error" not in fg_data:
                    fg_val = fg_data["value"]
                    fg_label = fg_data["label"]

            render_ticker(coins, fg_val, fg_label, tick_count)
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nTicker dihentikan.")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Live Crypto Price Ticker")
    parser.add_argument("--coins", nargs="+", help="Koin yang dipantau, contoh: --coins btc eth sol")
    parser.add_argument("--interval", type=int, default=10, help="Detik antar update (default: 10)")
    args = parser.parse_args()

    COIN_MAP = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "bnb": "binancecoin", "xrp": "ripple", "doge": "dogecoin",
        "ada": "cardano", "avax": "avalanche-2", "link": "chainlink",
        "dot": "polkadot", "matic": "matic-network",
    }

    if args.coins:
        coins = [COIN_MAP.get(c.lower(), c.lower()) for c in args.coins]
    else:
        coins = DEFAULT_COINS

    run_ticker(coins, interval=max(args.interval, 5))  # minimal 5 detik, hindari rate limit


if __name__ == "__main__":
    main()
