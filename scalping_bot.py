"""
scalping_bot.py — Scanner sinyal scalping otomatis.

Mode:
  python scalping_bot.py              → scan top 20 koin, tampilkan sinyal
  python scalping_bot.py --coin btc   → analisis 1 koin spesifik
  python scalping_bot.py --watch      → scan setiap 15 menit, notif Telegram
  python scalping_bot.py --coins btc eth sol bnb → scan koin pilihan

Output:
  - Sinyal LONG/SHORT/WAIT
  - Entry price, TP1, TP2, Stop Loss
  - R/R ratio
  - Strength score 0-100
  - Semua alasan teknikal
"""

import time
import argparse
from datetime import datetime
from tools import get_fear_and_greed, get_top_coins_by_market_cap
from scalping_engine import analyze_scalp, scan_scalp_opportunities
from telegram_bot import send_message

DEFAULT_COINS = [
    "bitcoin", "ethereum", "solana", "binancecoin",
    "ripple", "cardano", "avalanche-2", "chainlink",
    "polkadot", "dogecoin", "matic-network", "uniswap",
    "cosmos", "near", "arbitrum", "optimism",
]


def format_signal_terminal(sig) -> str:
    """Format sinyal untuk tampilan terminal."""
    bar = "█" * (sig.strength // 10) + "░" * (10 - sig.strength // 10)
    direction = "▲ LONG " if sig.signal == "LONG" else "▼ SHORT" if sig.signal == "SHORT" else "◆ WAIT "

    return (
        f"\n{'='*55}\n"
        f"  {direction}  {sig.symbol:<8}  Strength: {bar} {sig.strength}%\n"
        f"{'='*55}\n"
        f"  Entry : ${sig.entry_price:>14,.4f}\n"
        f"  TP1   : ${sig.tp1:>14,.4f}  (+{sig.tp1_pct():.2f}%)\n"
        f"  TP2   : ${sig.tp2:>14,.4f}  (+{sig.tp2_pct():.2f}%)\n"
        f"  SL    : ${sig.stop_loss:>14,.4f}  (-{sig.risk_pct():.2f}%)\n"
        f"  R/R   : {'1:' + str(sig.rr_ratio):>15}\n"
        f"{'─'*55}\n"
        f"  RSI    : {sig.rsi:<8}  MACD  : {sig.macd_trend}\n"
        f"  Volume : {sig.volume_signal}\n"
        f"  F&G    : {sig.fear_greed}/100\n"
        f"{'─'*55}\n"
        f"  Alasan:\n" +
        "\n".join(f"  • {r}" for r in sig.reasons) +
        f"\n{'─'*55}"
    )


def format_signal_telegram(sig) -> str:
    """Format sinyal untuk Telegram dengan HTML."""
    emoji = "🟢" if sig.signal == "LONG" else "🔴" if sig.signal == "SHORT" else "⚪"
    bar = "▓" * (sig.strength // 10) + "░" * (10 - sig.strength // 10)
    sr_note = " (level S/R asli)" if getattr(sig, "sr_used", False) else " (estimasi ATR)"

    reasons_text = "\n".join(f"• {r}" for r in sig.reasons)

    mtf_line = ""
    if getattr(sig, "mtf_confluence", "UNKNOWN") != "UNKNOWN":
        mtf_line = f"\n<b>Multi-TF:</b> {sig.mtf_confluence} ({sig.mtf_score}/3 searah)"
        if getattr(sig, "mtf_warning", None):
            mtf_line += f"\n⚠️ {sig.mtf_warning}"

    return (
        f"{emoji} <b>SCALP {sig.signal} — {sig.symbol}</b>\n"
        f"Confidence: <code>{bar}</code> {sig.strength}%{mtf_line}\n\n"
        f"<b>Entry :</b> <code>${sig.entry_price:,.4f}</code>\n"
        f"<b>TP1   :</b> <code>${sig.tp1:,.4f}</code> (+{sig.tp1_pct():.2f}%)\n"
        f"<b>TP2   :</b> <code>${sig.tp2:,.4f}</code> (+{sig.tp2_pct():.2f}%)\n"
        f"<b>SL    :</b> <code>${sig.stop_loss:,.4f}</code> (-{sig.risk_pct():.2f}%){sr_note}\n"
        f"<b>R/R   :</b> 1:{sig.rr_ratio}\n\n"
        f"RSI: {sig.rsi} | MACD: {sig.macd_trend}\n"
        f"Volume: {sig.volume_signal}\n"
        f"Fear &amp; Greed: {sig.fear_greed}/100\n\n"
        f"<b>Analisis:</b>\n{reasons_text}\n\n"
        f"<i>⚠️ Bukan financial advice. Eksekusi manual, gunakan risk management!</i>"
    )


def run_scan(coins: list, verbose: bool = True, notify_telegram: bool = False) -> list:
    """Scan koin dan tampilkan sinyal."""
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{now}] Scanning {len(coins)} koin untuk sinyal scalping...")

    # Ambil Fear & Greed sekali
    fg = get_fear_and_greed()
    fg_val = fg.get("value") if "error" not in fg else None
    if fg_val:
        print(f"  Fear & Greed: {fg_val} ({fg.get('label')})")

    print(f"\n  {'Koin':<14} {'Sinyal':<8} {'Strength':>10} {'Entry':>14}")
    print(f"  {'─'*55}")

    signals = []
    for coin in coins:
        sig = analyze_scalp(coin, fg_val)
        if not sig:
            continue

        arrow = "▲" if sig.signal == "LONG" else "▼" if sig.signal == "SHORT" else "◆"
        strength_bar = "█" * (sig.strength // 20)
        print(f"  {sig.symbol:<14} {arrow} {sig.signal:<7} {sig.strength:>3}% {strength_bar:<5} ${sig.entry_price:>12,.4f}")

        if sig.signal != "WAIT":
            signals.append(sig)

    # Tampilkan detail sinyal kuat
    strong = [s for s in signals if s.strength >= 55]
    if strong:
        print(f"\n  Ditemukan {len(strong)} sinyal kuat:\n")
        for sig in sorted(strong, key=lambda x: x.strength, reverse=True):
            print(format_signal_terminal(sig))

            if notify_telegram:
                send_message(format_signal_telegram(sig))
                time.sleep(1)
    else:
        print(f"\n  Tidak ada sinyal scalping kuat saat ini. Tunggu setup yang lebih jelas.")

    return strong


def analyze_single(coin: str) -> None:
    """Analisis mendalam satu koin."""
    print(f"\nMenganalisis {coin.upper()}...")
    fg = get_fear_and_greed()
    fg_val = fg.get("value") if "error" not in fg else None

    sig = analyze_scalp(coin, fg_val)
    if not sig:
        print(f"Gagal analisis {coin}. Pastikan nama koin benar.")
        return

    print(format_signal_terminal(sig))


def main():
    parser = argparse.ArgumentParser(description="Crypto Scalping Signal Scanner")
    parser.add_argument("--coin",   type=str, help="Analisis 1 koin: --coin btc")
    parser.add_argument("--coins",  nargs="+", help="Scan koin pilihan: --coins btc eth sol")
    parser.add_argument("--top",    type=int, default=20, help="Scan top N koin (default: 20)")
    parser.add_argument("--watch",  action="store_true", help="Mode watch: scan setiap 15 menit")
    parser.add_argument("--notify", action="store_true", help="Kirim sinyal ke Telegram")
    args = parser.parse_args()

    print("=" * 55)
    print("  Crypto Scalping Signal Scanner")
    print("  RSI + MACD + BB + EMA + Volume + Fear&Greed")
    print("=" * 55)

    if args.coin:
        analyze_single(args.coin)
        return

    if args.coins:
        coins = [c.lower() for c in args.coins]
    else:
        print(f"\nFetching top {args.top} koin...")
        top = get_top_coins_by_market_cap(args.top)
        coins = [c["name"].lower().replace(" ", "-") for c in top.get("coins", [])]
        if not coins:
            coins = DEFAULT_COINS[:args.top]

    if args.watch:
        interval = 900  # 15 menit
        print(f"\nMode Watch aktif — scan setiap {interval//60} menit")
        print("Ctrl+C untuk berhenti\n")
        if args.notify:
            send_message("🎯 <b>Scalping Scanner aktif!</b>\nScan setiap 15 menit.")
        while True:
            try:
                run_scan(coins, notify_telegram=args.notify)
                print(f"\nTidur {interval//60} menit...")
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\nScanner dihentikan.")
                break
    else:
        run_scan(coins, notify_telegram=args.notify)


if __name__ == "__main__":
    main()
