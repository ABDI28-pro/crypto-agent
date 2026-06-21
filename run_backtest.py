"""
run_backtest.py — CLI untuk jalankan backtest.

Cara pakai:
  python run_backtest.py --coin btc                  → backtest BTC 90 hari
  python run_backtest.py --coin eth --days 180        → backtest 180 hari
  python run_backtest.py --coins btc eth sol bnb      → backtest banyak koin sekaligus
  python run_backtest.py --coin btc --detail          → tampilkan semua trade individual
"""

import argparse
import time
from backtest_engine import run_backtest


def print_result(result, show_detail: bool = False):
    if result is None:
        print("  Gagal — data historis tidak cukup.")
        return

    print(f"\n{result.summary()}")

    if result.total_trades == 0:
        print("  Tidak ada trade yang ter-generate dalam periode ini.\n")
        return

    # Breakdown exit reason
    tp_count = sum(1 for t in result.trades if t.exit_reason == "TP1")
    sl_count = sum(1 for t in result.trades if t.exit_reason == "SL")
    timeout_count = sum(1 for t in result.trades if t.exit_reason == "TIMEOUT")
    print(f"Exit breakdown  : TP={tp_count} | SL={sl_count} | Timeout={timeout_count}\n")

    if show_detail:
        print(f"{'Time':<20}{'Dir':<7}{'Entry':>12}{'Exit':>12}{'Reason':<10}{'PnL%':>8}")
        print("-" * 75)
        for t in result.trades:
            time_str = t.entry_time[:16]
            print(f"{time_str:<20}{t.direction:<7}{t.entry_price:>12,.4f}{t.exit_price:>12,.4f}{t.exit_reason:<10}{t.pnl_pct:>+7.2f}%")
        print()


def main():
    parser = argparse.ArgumentParser(description="Crypto Scalping Strategy Backtester")
    parser.add_argument("--coin", type=str, help="Backtest 1 koin: --coin btc")
    parser.add_argument("--coins", nargs="+", help="Backtest banyak koin: --coins btc eth sol")
    parser.add_argument("--days", type=int, default=30, help="Periode historis dalam hari (default: 30, gunakan 3-30 untuk candle 4H)")
    parser.add_argument("--detail", action="store_true", help="Tampilkan semua trade individual")
    args = parser.parse_args()

    print("=" * 55)
    print("  Crypto Scalping Strategy Backtester")
    print(f"  Periode: {args.days} hari | Data: CoinGecko 4H candle")
    print("=" * 55)

    coins = []
    if args.coin:
        coins = [args.coin]
    elif args.coins:
        coins = args.coins
    else:
        coins = ["bitcoin", "ethereum", "solana"]

    results = []
    for i, coin in enumerate(coins):
        if i > 0:
            print(f"\nMenunggu 8 detik (hindari rate limit CoinGecko)...")
            time.sleep(8)
        print(f"\nMenjalankan backtest {coin.upper()}...")
        result = run_backtest(coin, days=args.days)
        if result:
            results.append(result)
            print_result(result, show_detail=args.detail)

    if len(results) > 1:
        print("=" * 55)
        print("  RINGKASAN PERBANDINGAN")
        print("=" * 55)
        print(f"{'Coin':<12}{'Trades':>8}{'Win Rate':>10}{'P.Factor':>10}{'Return':>10}{'MaxDD':>8}")
        print("-" * 60)
        for r in sorted(results, key=lambda x: x.total_return_pct, reverse=True):
            print(f"{r.coin.upper():<12}{r.total_trades:>8}{r.win_rate:>9.1f}%{r.profit_factor:>10.2f}{r.total_return_pct:>+9.2f}%{r.max_drawdown_pct:>7.1f}%")
        print()


if __name__ == "__main__":
    main()
