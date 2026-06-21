"""
scheduler.py — Jalankan agent otomatis, monitor top 100 koin by market cap.

Mode:
  python scheduler.py          → loop otomatis setiap jam
  python scheduler.py --once   → cek sekali sekarang
  python scheduler.py --test   → test koneksi Telegram
  python scheduler.py --top 50 → cek top 50 koin saja
"""

import time
import argparse
import requests
from datetime import datetime
from tools import get_fear_and_greed, get_market_overview
from signal_engine import analyze, should_notify
from telegram_bot import send_signal, send_message, test_connection

COINGECKO = "https://api.coingecko.com/api/v3"
HEADERS = {"User-Agent": "CryptoAgent/1.0"}
CHECK_INTERVAL_SECONDS = 3600  # 1 jam


def fetch_top_coins(limit: int = 100) -> list:
    """
    Ambil top N koin by market cap dari CoinGecko.
    Return list of dict: {id, symbol, name, price, change_24h, market_cap, volume}
    """
    print(f"  Fetching top {limit} koin by market cap...")
    try:
        r = requests.get(
            f"{COINGECKO}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            },
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        coins = []
        for c in r.json():
            coins.append({
                "id": c["id"],
                "symbol": c["symbol"].upper(),
                "name": c["name"],
                "price_usd": c["current_price"] or 0,
                "change_24h_pct": c.get("price_change_percentage_24h") or 0,
                "market_cap_usd": c.get("market_cap") or 0,
                "volume_24h_usd": c.get("total_volume") or 0,
            })
        print(f"  OK — {len(coins)} koin berhasil diambil")
        return coins
    except Exception as e:
        print(f"  ERROR fetch top coins: {e}")
        return []


def run_check(limit: int = 100, verbose: bool = True) -> list:
    """
    Cek top N koin, analisis sinyal, kirim notif ke Telegram kalau ada sinyal kuat.
    """
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{now}] Memulai pengecekan top {limit} koin...\n")

    # Ambil Fear & Greed sekali untuk semua koin
    fg_data = get_fear_and_greed()
    fg_val = fg_data.get("value") if "error" not in fg_data else None
    if fg_val:
        print(f"  Fear & Greed: {fg_val} ({fg_data.get('label')})\n")

    # Fetch semua koin sekaligus
    coins = fetch_top_coins(limit)
    if not coins:
        print("  Gagal fetch data koin.")
        return []

    signals_sent = []
    strong_signals = []

    print(f"  {'#':<4} {'Symbol':<8} {'Price':>12} {'24h':>8}  Sinyal")
    print(f"  {'-'*55}")

    for i, coin in enumerate(coins, 1):
        price_data = {
            "price_usd": coin["price_usd"],
            "change_24h_pct": coin["change_24h_pct"],
            "market_cap_usd": coin["market_cap_usd"],
            "volume_24h_usd": coin["volume_24h_usd"],
        }

        signal = analyze(coin["id"], price_data, fg_val)

        # Print ringkas di terminal
        arrow = "▲" if signal.change_24h >= 0 else "▼"
        change_str = f"{arrow}{abs(signal.change_24h):.1f}%"
        signal_str = f"{signal.signal_type} ({signal.strength})"

        if verbose:
            marker = " ◄" if should_notify(signal) else ""
            print(f"  {i:<4} {coin['symbol']:<8} ${coin['price_usd']:>11,.4f} {change_str:>8}  {signal_str}{marker}")

        # Kumpulkan sinyal kuat
        if should_notify(signal):
            strong_signals.append((coin, signal))

    print(f"\n  Ditemukan {len(strong_signals)} sinyal kuat dari {len(coins)} koin.")

    # Kirim sinyal ke Telegram (max 10 per cek, hindari spam)
    MAX_NOTIF = 10
    if strong_signals:
        print(f"  Mengirim {min(len(strong_signals), MAX_NOTIF)} sinyal ke Telegram...")

        # Sort by strength: STRONG dulu, baru MODERATE
        strong_signals.sort(key=lambda x: (
            0 if x[1].strength == "STRONG" else 1,
            -abs(x[1].change_24h)
        ))

        for coin, signal in strong_signals[:MAX_NOTIF]:
            result = send_signal(
                coin=f"{coin['name']} ({coin['symbol']})",
                price=signal.price,
                change_24h=signal.change_24h,
                signal_type=signal.signal_type,
                reason=signal.summary(),
                fear_greed=fg_val,
                rsi=signal.rsi,
                macd_trend=signal.macd_trend,
            )
            if "success" in result:
                signals_sent.append(signal)
                print(f"    ✓ {coin['symbol']} {signal.signal_type} dikirim")
            else:
                print(f"    ✗ {coin['symbol']} gagal: {result.get('error')}")

            time.sleep(0.5)  # jangan spam Telegram terlalu cepat

    elif verbose:
        print("  Tidak ada sinyal kuat saat ini.")

    return signals_sent


def main():
    parser = argparse.ArgumentParser(description="Crypto Signal Scheduler — Top 100 Coins")
    parser.add_argument("--once",   action="store_true", help="Cek sekali lalu keluar")
    parser.add_argument("--test",   action="store_true", help="Test koneksi Telegram")
    parser.add_argument("--top",    type=int, default=100, help="Jumlah koin top (default: 100)")
    args = parser.parse_args()

    if args.test:
        print("Testing koneksi Telegram...")
        ok = test_connection()
        print("BERHASIL! Cek Telegram kamu." if ok else "GAGAL. Cek .env kamu.")
        return

    if args.once:
        run_check(limit=args.top)
        return

    # Mode loop
    print("=" * 55)
    print(f"  Crypto Signal Bot — Top {args.top} Coins")
    print(f"  Cek setiap {CHECK_INTERVAL_SECONDS // 60} menit")
    print("  Ctrl+C untuk berhenti")
    print("=" * 55)

    send_message(
        f"<b>Crypto Signal Bot aktif!</b>\n"
        f"Monitoring top {args.top} koin by market cap.\n"
        f"Cek setiap jam, sinyal kuat akan dikirim otomatis."
    )

    check_count = 0
    while True:
        try:
            check_count += 1
            run_check(limit=args.top)
            print(f"\nTidur {CHECK_INTERVAL_SECONDS // 60} menit...")
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\nBot dihentikan.")
            send_message("Crypto Signal Bot dihentikan.")
            break
        except Exception as e:
            print(f"Error: {e} — coba lagi dalam 5 menit")
            time.sleep(300)


if __name__ == "__main__":
    main()
