"""
scalping_engine.py — Super Scalping Engine v2.

Upgrade dari versi sebelumnya:
  1. Entry & SL ditempatkan di level Support/Resistance asli, bukan cuma ATR
  2. Sinyal dikonfirmasi 3 timeframe (1H, 4H, 1D) — confluence based
  3. Confidence score lebih jujur: makin banyak faktor align, makin tinggi

Strategi:
  - RSI, MACD, Bollinger Bands, EMA, Volume (timeframe utama)
  - Support/Resistance (untuk entry & SL presisi)
  - Multi-timeframe confluence (filter sinyal palsu)
  - Fear & Greed (sentimen makro)
"""

import requests
import pandas as pd
import ta
from dataclasses import dataclass
from support_resistance import get_support_resistance
from multi_timeframe import analyze_multi_timeframe

COINGECKO = "https://api.coingecko.com/api/v3"
HEADERS = {"User-Agent": "CryptoAgent/1.0"}

COIN_IDS = {
    "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
    "bnb": "binancecoin", "xrp": "ripple", "doge": "dogecoin",
    "ada": "cardano", "avax": "avalanche-2", "link": "chainlink",
    "dot": "polkadot", "matic": "matic-network", "uni": "uniswap",
    "atom": "cosmos", "near": "near", "arb": "arbitrum",
    "op": "optimism", "sui": "sui", "apt": "aptos",
}


@dataclass
class ScalpSignal:
    coin: str
    symbol: str
    timeframe: str
    signal: str              # LONG, SHORT, WAIT
    strength: int             # 0-100, confidence score
    entry_price: float
    tp1: float
    tp2: float
    stop_loss: float
    rr_ratio: float
    rsi: float
    macd_trend: str
    volume_signal: str
    reasons: list
    fear_greed: int = None
    sr_used: bool = False           # apakah SL/TP pakai level S/R asli
    mtf_confluence: str = "UNKNOWN" # BULLISH/BEARISH/MIXED dari multi-timeframe
    mtf_score: int = 0              # 0-3, berapa timeframe yang searah
    mtf_warning: str = None

    def risk_pct(self) -> float:
        return abs(self.entry_price - self.stop_loss) / self.entry_price * 100

    def tp1_pct(self) -> float:
        return abs(self.tp1 - self.entry_price) / self.entry_price * 100

    def tp2_pct(self) -> float:
        return abs(self.tp2 - self.entry_price) / self.entry_price * 100

    def summary_text(self) -> str:
        signal_emoji = "🟢 LONG" if self.signal == "LONG" else "🔴 SHORT" if self.signal == "SHORT" else "⚪ WAIT"
        sr_note = "(level S/R asli)" if self.sr_used else "(estimasi ATR)"
        lines = [
            f"{signal_emoji} | Confidence: {self.strength}/100",
            f"",
            f"Entry  : ${self.entry_price:,.4f}",
            f"TP1    : ${self.tp1:,.4f} (+{self.tp1_pct():.2f}%)",
            f"TP2    : ${self.tp2:,.4f} (+{self.tp2_pct():.2f}%)",
            f"SL     : ${self.stop_loss:,.4f} (-{self.risk_pct():.2f}%) {sr_note}",
            f"R/R    : 1:{self.rr_ratio:.1f}",
            f"",
            f"Multi-timeframe: {self.mtf_confluence} ({self.mtf_score}/3 searah)",
        ]
        if self.mtf_warning:
            lines.append(f"⚠️  {self.mtf_warning}")
        lines += [
            f"",
            f"RSI    : {self.rsi}",
            f"MACD   : {self.macd_trend}",
            f"Volume : {self.volume_signal}",
        ]
        if self.fear_greed is not None:
            lines.append(f"F&G    : {self.fear_greed}/100")
        lines.append("")
        lines.append("Alasan:")
        for r in self.reasons:
            lines.append(f"• {r}")
        return "\n".join(lines)


def fetch_ohlcv(coin_id: str, days: int = 14) -> pd.DataFrame:
    try:
        r = requests.get(
            f"{COINGECKO}/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": days},
            headers=HEADERS, timeout=10,
        )
        r.raise_for_status()
        df = pd.DataFrame(r.json(), columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["volume"] = (df["high"] - df["low"]) * df["close"]
        return df.sort_values("timestamp").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def calc_all_indicators(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 30:
        return {}

    close, high, low, volume = df["close"], df["high"], df["low"], df["volume"]

    rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi()
    rsi_val = round(float(rsi.iloc[-1]), 2)
    rsi_prev = round(float(rsi.iloc[-2]), 2)

    macd_ind = ta.trend.MACD(close=close)
    macd_line = float(macd_ind.macd().iloc[-1])
    signal_line = float(macd_ind.macd_signal().iloc[-1])
    macd_hist = float(macd_ind.macd_diff().iloc[-1])
    macd_hist_prev = float(macd_ind.macd_diff().iloc[-2])

    bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    bb_pct = float(bb.bollinger_pband().iloc[-1])

    ema9 = float(ta.trend.EMAIndicator(close=close, window=9).ema_indicator().iloc[-1])
    ema21 = float(ta.trend.EMAIndicator(close=close, window=21).ema_indicator().iloc[-1])
    ema50 = float(ta.trend.EMAIndicator(close=close, window=50).ema_indicator().iloc[-1])

    atr = float(ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1])

    vol_ma = volume.rolling(20).mean().iloc[-1]
    vol_current = volume.iloc[-1]
    vol_ratio = vol_current / vol_ma if vol_ma > 0 else 1

    current_price = float(close.iloc[-1])

    return {
        "price": current_price, "rsi": rsi_val, "rsi_prev": rsi_prev,
        "macd_line": round(macd_line, 6), "signal_line": round(signal_line, 6),
        "macd_hist": round(macd_hist, 6), "macd_hist_prev": round(macd_hist_prev, 6),
        "bb_pct": round(bb_pct, 3),
        "ema9": round(ema9, 4), "ema21": round(ema21, 4), "ema50": round(ema50, 4),
        "atr": round(atr, 4), "vol_ratio": round(vol_ratio, 2),
    }


def analyze_scalp(coin: str, fear_greed: int = None, use_mtf: bool = True) -> ScalpSignal:
    """
    Analisis lengkap scalping dengan S/R levels + multi-timeframe confirmation.
    """
    coin_id = COIN_IDS.get(coin.lower(), coin.lower())
    symbol = coin.upper()

    df = fetch_ohlcv(coin_id, days=14)
    if df.empty:
        return None

    ind = calc_all_indicators(df)
    if not ind:
        return None

    price = ind["price"]
    reasons = []
    long_score = 0
    short_score = 0

    # ── RSI ──────────────────────────────────────────────────
    rsi, rsi_prev = ind["rsi"], ind["rsi_prev"]
    rsi_rising = rsi > rsi_prev

    if rsi < 25:
        reasons.append(f"RSI {rsi} — Sangat oversold")
        long_score += 25
    elif rsi < 35:
        reasons.append(f"RSI {rsi} — Oversold")
        long_score += 17
    elif rsi < 45 and rsi_rising:
        reasons.append(f"RSI {rsi} naik dari zona rendah")
        long_score += 8
    elif rsi > 75:
        reasons.append(f"RSI {rsi} — Sangat overbought")
        short_score += 25
    elif rsi > 65:
        reasons.append(f"RSI {rsi} — Overbought")
        short_score += 17
    elif rsi > 55 and not rsi_rising:
        reasons.append(f"RSI {rsi} turun dari zona tinggi")
        short_score += 8
    else:
        reasons.append(f"RSI {rsi} — Zona netral")

    # ── MACD ─────────────────────────────────────────────────
    macd_hist, macd_hist_prev = ind["macd_hist"], ind["macd_hist_prev"]
    macd_line, signal_line = ind["macd_line"], ind["signal_line"]

    bullish_cross = macd_line > signal_line and macd_hist > 0 and macd_hist > macd_hist_prev
    bearish_cross = macd_line < signal_line and macd_hist < 0 and macd_hist < macd_hist_prev

    if bullish_cross:
        reasons.append("MACD bullish crossover terkonfirmasi")
        long_score += 20
        macd_trend = "BULLISH_CROSS"
    elif bearish_cross:
        reasons.append("MACD bearish crossover terkonfirmasi")
        short_score += 20
        macd_trend = "BEARISH_CROSS"
    elif macd_line > signal_line:
        reasons.append("MACD di atas signal line")
        long_score += 8
        macd_trend = "BULLISH"
    else:
        reasons.append("MACD di bawah signal line")
        short_score += 8
        macd_trend = "BEARISH"

    # ── Bollinger Bands ──────────────────────────────────────
    bb_pct = ind["bb_pct"]
    if bb_pct < 0.1:
        reasons.append("Harga di lower Bollinger Band — potensi bounce")
        long_score += 12
    elif bb_pct > 0.9:
        reasons.append("Harga di upper Bollinger Band — potensi koreksi")
        short_score += 12

    # ── EMA Trend ────────────────────────────────────────────
    ema9, ema21, ema50 = ind["ema9"], ind["ema21"], ind["ema50"]
    if ema9 > ema21 > ema50 and price > ema9:
        reasons.append("EMA9>EMA21>EMA50 — uptrend kuat")
        long_score += 12
    elif ema9 < ema21 < ema50 and price < ema9:
        reasons.append("EMA9<EMA21<EMA50 — downtrend kuat")
        short_score += 12

    # ── Volume ───────────────────────────────────────────────
    vol_ratio = ind["vol_ratio"]
    if vol_ratio >= 1.5:
        volume_signal = f"TINGGI ({vol_ratio:.1f}x)"
        reasons.append(f"Volume {vol_ratio:.1f}x rata-rata — konfirmasi kuat")
        bonus = 8
        long_score += bonus if long_score > short_score else 0
        short_score += bonus if short_score > long_score else 0
    elif vol_ratio >= 1.2:
        volume_signal = f"NORMAL ({vol_ratio:.1f}x)"
    else:
        volume_signal = f"RENDAH ({vol_ratio:.1f}x)"
        reasons.append("Volume rendah — konfirmasi lemah")
        long_score = int(long_score * 0.85)
        short_score = int(short_score * 0.85)

    # ── Fear & Greed ─────────────────────────────────────────
    if fear_greed is not None:
        if fear_greed <= 20:
            reasons.append(f"F&G {fear_greed} = Extreme Fear — dukung LONG")
            long_score += 12
        elif fear_greed <= 35:
            long_score += 5
        elif fear_greed >= 80:
            reasons.append(f"F&G {fear_greed} = Extreme Greed — dukung SHORT")
            short_score += 12
        elif fear_greed >= 65:
            short_score += 5

    # ── Multi-timeframe confirmation ────────────────────────
    mtf_confluence, mtf_score, mtf_warning = "UNKNOWN", 0, None
    if use_mtf:
        try:
            mtf = analyze_multi_timeframe(coin_id)
            mtf_confluence = mtf["confluence"]
            mtf_score = mtf["confluence_score"]
            mtf_warning = mtf["warning"]

            if mtf_confluence == "BULLISH":
                bonus = mtf_score * 8  # 2 TF align = +16, 3 TF = +24
                long_score += bonus
                reasons.append(f"Multi-timeframe BULLISH ({mtf_score}/3 timeframe searah)")
            elif mtf_confluence == "BEARISH":
                bonus = mtf_score * 8
                short_score += bonus
                reasons.append(f"Multi-timeframe BEARISH ({mtf_score}/3 timeframe searah)")
            else:
                reasons.append("Multi-timeframe MIXED — sinyal kurang solid")
                long_score = int(long_score * 0.7)
                short_score = int(short_score * 0.7)

            if mtf_warning:
                reasons.append(f"⚠️ {mtf_warning}")
        except Exception as e:
            reasons.append(f"Multi-timeframe check gagal: {e}")

    # ── Support/Resistance untuk entry & SL presisi ──────────
    sr = get_support_resistance(df, price)
    sr_used = bool(sr.get("nearest_support") or sr.get("nearest_resistance"))

    atr = ind["atr"]
    total_score = long_score + short_score

    if long_score > short_score and long_score >= 45:
        signal = "LONG"
        strength = min(int(long_score / max(total_score, 1) * 100), 97)
        entry = price

        # SL: pakai support terdekat kalau ada dan masuk akal, fallback ke ATR
        if sr.get("nearest_support") and (entry - sr["nearest_support"]) / entry < 0.05:
            sl = round(sr["nearest_support"] * 0.998, 6)  # sedikit di bawah support
            reasons.append(f"SL ditempatkan di bawah support ${sr['nearest_support']:,.4f} (strength {sr['support_strength']})")
        else:
            sl = round(entry - (atr * 1.5), 6)

        # TP: pakai resistance terdekat kalau masuk akal, fallback ke ATR
        if sr.get("nearest_resistance") and (sr["nearest_resistance"] - entry) / entry < 0.08:
            tp1 = round(sr["nearest_resistance"] * 0.998, 6)
            reasons.append(f"TP1 ditempatkan di bawah resistance ${sr['nearest_resistance']:,.4f}")
        else:
            tp1 = round(entry + (atr * 1.5), 6)
        tp2 = round(entry + (atr * 3.0), 6)

        risk = entry - sl
        reward = tp1 - entry
        rr = round(reward / risk, 1) if risk > 0 else 1.0

    elif short_score > long_score and short_score >= 45:
        signal = "SHORT"
        strength = min(int(short_score / max(total_score, 1) * 100), 97)
        entry = price

        if sr.get("nearest_resistance") and (sr["nearest_resistance"] - entry) / entry < 0.05:
            sl = round(sr["nearest_resistance"] * 1.002, 6)
            reasons.append(f"SL ditempatkan di atas resistance ${sr['nearest_resistance']:,.4f} (strength {sr['resistance_strength']})")
        else:
            sl = round(entry + (atr * 1.5), 6)

        if sr.get("nearest_support") and (entry - sr["nearest_support"]) / entry < 0.08:
            tp1 = round(sr["nearest_support"] * 1.002, 6)
            reasons.append(f"TP1 ditempatkan di atas support ${sr['nearest_support']:,.4f}")
        else:
            tp1 = round(entry - (atr * 1.5), 6)
        tp2 = round(entry - (atr * 3.0), 6)

        risk = sl - entry
        reward = entry - tp1
        rr = round(reward / risk, 1) if risk > 0 else 1.0

    else:
        signal = "WAIT"
        strength = 0
        entry = price
        sl = round(price * 0.98, 6)
        tp1 = round(price * 1.02, 6)
        tp2 = round(price * 1.04, 6)
        rr = 1.0
        sr_used = False
        reasons.append("Sinyal belum cukup kuat atau timeframe konflik — tunggu konfirmasi")

    return ScalpSignal(
        coin=coin_id, symbol=symbol, timeframe="Multi-TF (1H/4H/1D)",
        signal=signal, strength=strength,
        entry_price=entry, tp1=tp1, tp2=tp2, stop_loss=sl, rr_ratio=rr,
        rsi=rsi, macd_trend=macd_trend, volume_signal=volume_signal,
        reasons=reasons, fear_greed=fear_greed,
        sr_used=sr_used, mtf_confluence=mtf_confluence,
        mtf_score=mtf_score, mtf_warning=mtf_warning,
    )


def scan_scalp_opportunities(coins: list, fear_greed: int = None) -> list:
    """Scan beberapa koin, return hanya sinyal kuat (strength >= 55)."""
    results = []
    for coin in coins:
        sig = analyze_scalp(coin, fear_greed)
        if sig and sig.signal != "WAIT" and sig.strength >= 55:
            results.append(sig)
    results.sort(key=lambda x: x.strength, reverse=True)
    return results
