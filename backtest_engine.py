"""
backtest_engine.py — Backtest strategi scalping ke data historis.

Cara kerja:
  1. Ambil data OHLC historis (30-90 hari)
  2. Jalankan signal_engine analisis di SETIAP titik waktu (rolling window)
  3. Simulasikan: kalau sinyal LONG/SHORT muncul, apakah TP atau SL kena duluan?
  4. Hitung statistik: win rate, profit factor, max drawdown, avg R/R

PENTING: Backtest pakai data CoinGecko (4H candle), hasilnya estimasi —
bukan jaminan performa real karena slippage, fee, dan likuiditas tidak disimulasikan.
"""

import requests
import pandas as pd
import ta
import time
from dataclasses import dataclass, field
from datetime import datetime

COINGECKO = "https://api.coingecko.com/api/v3"
HEADERS = {"User-Agent": "CryptoAgent/1.0"}

COIN_IDS = {
    "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
    "bnb": "binancecoin", "xrp": "ripple", "doge": "dogecoin",
    "ada": "cardano", "avax": "avalanche-2", "link": "chainlink",
    "dot": "polkadot",
}


@dataclass
class Trade:
    entry_time: str
    direction: str        # LONG / SHORT
    entry_price: float
    exit_price: float
    exit_reason: str      # TP1, TP2, SL, TIMEOUT
    pnl_pct: float
    bars_held: int


@dataclass
class BacktestResult:
    coin: str
    period_days: int
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    total_return_pct: float
    max_drawdown_pct: float
    trades: list = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Backtest {self.coin.upper()} ({self.period_days} hari)\n"
            f"{'='*45}\n"
            f"Total trades    : {self.total_trades}\n"
            f"Win rate        : {self.win_rate:.1f}% ({self.wins}W / {self.losses}L)\n"
            f"Avg win         : +{self.avg_win_pct:.2f}%\n"
            f"Avg loss        : {self.avg_loss_pct:.2f}%\n"
            f"Profit factor   : {self.profit_factor:.2f}\n"
            f"Total return    : {self.total_return_pct:+.2f}%\n"
            f"Max drawdown    : -{self.max_drawdown_pct:.2f}%\n"
        )


def fetch_historical(coin_id: str, days: int = 90, max_retries: int = 3) -> pd.DataFrame:
    """Fetch data historis untuk backtest, dengan retry kalau kena rate limit."""
    for attempt in range(max_retries):
        try:
            r = requests.get(
                f"{COINGECKO}/coins/{coin_id}/ohlc",
                params={"vs_currency": "usd", "days": days},
                headers=HEADERS, timeout=15,
            )
            if r.status_code == 429:
                wait = 15 * (attempt + 1)
                print(f"  Rate limit kena, menunggu {wait} detik... (percobaan {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            df = pd.DataFrame(r.json(), columns=["timestamp", "open", "high", "low", "close"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df["volume"] = (df["high"] - df["low"]) * df["close"]
            return df.sort_values("timestamp").reset_index(drop=True)
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f"Fetch error: {e}")
                return pd.DataFrame()
            time.sleep(5)
    return pd.DataFrame()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Hitung semua indikator untuk seluruh dataset sekaligus (vectorized)."""
    df = df.copy()
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()

    macd = ta.trend.MACD(close=df["close"])
    df["macd_line"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()

    bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
    df["bb_pct"] = bb.bollinger_pband()

    df["ema9"] = ta.trend.EMAIndicator(close=df["close"], window=9).ema_indicator()
    df["ema21"] = ta.trend.EMAIndicator(close=df["close"], window=21).ema_indicator()

    df["atr"] = ta.volatility.AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=14
    ).average_true_range()

    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["vol_ratio"] = df["volume"] / df["vol_ma"]

    return df


def generate_signal_at_index(df: pd.DataFrame, i: int) -> str:
    """
    Replikasi logika scalping_engine tapi untuk satu baris data historis.
    Return: "LONG", "SHORT", atau "WAIT"
    """
    if i < 30:
        return "WAIT"

    row = df.iloc[i]
    prev = df.iloc[i - 1]

    if pd.isna(row["rsi"]) or pd.isna(row["macd_hist"]):
        return "WAIT"

    long_score = 0
    short_score = 0

    # RSI
    if row["rsi"] < 30:
        long_score += 25
    elif row["rsi"] > 70:
        short_score += 25

    # MACD crossover
    bullish_cross = row["macd_line"] > row["macd_signal"] and row["macd_hist"] > prev["macd_hist"]
    bearish_cross = row["macd_line"] < row["macd_signal"] and row["macd_hist"] < prev["macd_hist"]
    if bullish_cross:
        long_score += 20
    elif bearish_cross:
        short_score += 20

    # Bollinger Bands
    if row["bb_pct"] < 0.1:
        long_score += 15
    elif row["bb_pct"] > 0.9:
        short_score += 15

    # EMA trend
    if row["ema9"] > row["ema21"] and row["close"] > row["ema9"]:
        long_score += 10
    elif row["ema9"] < row["ema21"] and row["close"] < row["ema9"]:
        short_score += 10

    # Volume confirmation
    if row["vol_ratio"] >= 1.3:
        if long_score > short_score:
            long_score += 8
        else:
            short_score += 8

    if long_score >= 45 and long_score > short_score:
        return "LONG"
    elif short_score >= 45 and short_score > long_score:
        return "SHORT"
    return "WAIT"


def simulate_trade(df: pd.DataFrame, entry_idx: int, direction: str,
                    tp_atr_mult: float = 1.5, sl_atr_mult: float = 1.5,
                    max_bars: int = 20) -> Trade:
    """
    Simulasikan satu trade dari entry_idx, cek apakah TP atau SL kena duluan.
    """
    entry_row = df.iloc[entry_idx]
    entry_price = entry_row["close"]
    atr = entry_row["atr"] if not pd.isna(entry_row["atr"]) else entry_price * 0.02

    if direction == "LONG":
        tp = entry_price + (atr * tp_atr_mult)
        sl = entry_price - (atr * sl_atr_mult)
    else:
        tp = entry_price - (atr * tp_atr_mult)
        sl = entry_price + (atr * sl_atr_mult)

    exit_price = entry_price
    exit_reason = "TIMEOUT"
    bars_held = 0

    for j in range(entry_idx + 1, min(entry_idx + 1 + max_bars, len(df))):
        bars_held += 1
        bar = df.iloc[j]

        if direction == "LONG":
            if bar["low"] <= sl:
                exit_price = sl
                exit_reason = "SL"
                break
            if bar["high"] >= tp:
                exit_price = tp
                exit_reason = "TP1"
                break
        else:
            if bar["high"] >= sl:
                exit_price = sl
                exit_reason = "SL"
                break
            if bar["low"] <= tp:
                exit_price = tp
                exit_reason = "TP1"
                break
    else:
        # Timeout — exit di harga close terakhir yang dicek
        last_idx = min(entry_idx + max_bars, len(df) - 1)
        exit_price = df.iloc[last_idx]["close"]

    if direction == "LONG":
        pnl_pct = (exit_price - entry_price) / entry_price * 100
    else:
        pnl_pct = (entry_price - exit_price) / entry_price * 100

    return Trade(
        entry_time=str(entry_row["timestamp"]),
        direction=direction,
        entry_price=round(entry_price, 6),
        exit_price=round(exit_price, 6),
        exit_reason=exit_reason,
        pnl_pct=round(pnl_pct, 3),
        bars_held=bars_held,
    )


def run_backtest(coin: str, days: int = 30, cooldown_bars: int = 5) -> BacktestResult:
    """
    Jalankan backtest lengkap untuk satu koin.

    Args:
        coin          : nama koin
        days          : periode historis dalam hari.
                        PENTING — granularity CoinGecko otomatis:
                        days 1-2   → candle 30 menit (sangat banyak data)
                        days 3-30  → candle 4 jam (rekomendasi untuk scalping)
                        days >30   → candle 1 hari (data jadi sedikit/jarang)
        cooldown_bars : jeda minimal antar trade (hindari overlapping signals)
    """
    coin_id = COIN_IDS.get(coin.lower(), coin.lower())
    df = fetch_historical(coin_id, days)

    if df.empty or len(df) < 35:
        print(f"  Data tidak cukup ({len(df)} baris). Coba --days di antara 3-30 untuk candle 4 jam yang lebih rapat.")
        return None

    df = add_indicators(df)

    trades = []
    last_trade_idx = -999

    for i in range(30, len(df) - 1):
        if i - last_trade_idx < cooldown_bars:
            continue

        signal = generate_signal_at_index(df, i)
        if signal in ("LONG", "SHORT"):
            trade = simulate_trade(df, i, signal)
            trades.append(trade)
            last_trade_idx = i

    if not trades:
        return BacktestResult(
            coin=coin_id, period_days=days, total_trades=0,
            wins=0, losses=0, win_rate=0, avg_win_pct=0, avg_loss_pct=0,
            profit_factor=0, total_return_pct=0, max_drawdown_pct=0, trades=[],
        )

    wins = [t for t in trades if t.pnl_pct > 0]
    losses = [t for t in trades if t.pnl_pct <= 0]

    win_rate = len(wins) / len(trades) * 100
    avg_win = sum(t.pnl_pct for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.pnl_pct for t in losses) / len(losses) if losses else 0

    total_win_pnl = sum(t.pnl_pct for t in wins)
    total_loss_pnl = abs(sum(t.pnl_pct for t in losses))
    profit_factor = total_win_pnl / total_loss_pnl if total_loss_pnl > 0 else float('inf')

    # Equity curve untuk max drawdown
    equity = [0]
    for t in trades:
        equity.append(equity[-1] + t.pnl_pct)

    peak = equity[0]
    max_dd = 0
    for eq in equity:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

    return BacktestResult(
        coin=coin_id, period_days=days,
        total_trades=len(trades), wins=len(wins), losses=len(losses),
        win_rate=round(win_rate, 1),
        avg_win_pct=round(avg_win, 2), avg_loss_pct=round(avg_loss, 2),
        profit_factor=round(profit_factor, 2) if profit_factor != float('inf') else 99.9,
        total_return_pct=round(equity[-1], 2),
        max_drawdown_pct=round(max_dd, 2),
        trades=trades,
    )
