"""
signal_engine.py — Mesin sinyal trading dengan RSI + MACD + Price action.

Sinyal sekarang lebih akurat karena gabungkan 3 faktor:
  1. Perubahan harga 24 jam (momentum jangka pendek)
  2. RSI (kondisi overbought/oversold)
  3. MACD (arah trend dan momentum)
  4. Fear & Greed Index (sentimen pasar)
"""

from dataclasses import dataclass, field
from indicators import get_indicators


@dataclass
class Signal:
    coin: str
    price: float
    change_24h: float
    signal_type: str     # BUY, SELL, WATCH, HOLD
    strength: str        # STRONG, MODERATE, WEAK
    reasons: list
    rsi: float = None
    macd_trend: str = None
    fear_greed: int = None

    def summary(self) -> str:
        return "\n".join(f"• {r}" for r in self.reasons)


def analyze(coin: str, price_data: dict, fear_greed: int = None) -> Signal:
    """
    Analisis lengkap: price action + RSI + MACD + Fear & Greed.
    """
    change = price_data.get("change_24h_pct", 0)
    price = price_data.get("price_usd", 0)
    reasons = []
    score = 0.0

    # ── 1. Price action 24 jam ──────────────────────────────
    if change >= 10:
        reasons.append(f"Harga naik tajam +{change:.1f}% dalam 24 jam")
        score += 2
    elif change >= 5:
        reasons.append(f"Harga naik +{change:.1f}% dalam 24 jam")
        score += 1
    elif change >= 2:
        reasons.append(f"Harga naik moderat +{change:.1f}% dalam 24 jam")
        score += 0.5
    elif change <= -10:
        reasons.append(f"Harga turun tajam {change:.1f}% dalam 24 jam")
        score -= 2
    elif change <= -5:
        reasons.append(f"Harga turun {change:.1f}% dalam 24 jam")
        score -= 1
    elif change <= -2:
        reasons.append(f"Harga turun moderat {change:.1f}% dalam 24 jam")
        score -= 0.5
    else:
        reasons.append(f"Harga relatif stabil ({change:+.1f}%)")

    # ── 2. RSI + MACD dari indicators.py ───────────────────
    rsi_val = None
    macd_trend = None

    try:
        ind = get_indicators(coin)
        if "error" not in ind:
            rsi_val = ind["rsi"]["value"]
            macd_trend = ind["macd"].get("trend", "")
            combined = ind["combined_signal"]

            # RSI scoring
            if rsi_val <= 25:
                reasons.append(f"RSI {rsi_val} — Sangat oversold, peluang beli kuat")
                score += 2
            elif rsi_val <= 35:
                reasons.append(f"RSI {rsi_val} — Oversold, potensi reversal naik")
                score += 1
            elif rsi_val >= 80:
                reasons.append(f"RSI {rsi_val} — Sangat overbought, waspadai koreksi")
                score -= 2
            elif rsi_val >= 70:
                reasons.append(f"RSI {rsi_val} — Overbought, hati-hati reversal")
                score -= 1
            else:
                reasons.append(f"RSI {rsi_val} — Zona netral")

            # MACD scoring
            if macd_trend == "BULLISH":
                reasons.append("MACD bullish — momentum naik terkonfirmasi")
                score += 1.5
            elif macd_trend == "BEARISH":
                reasons.append("MACD bearish — momentum turun terkonfirmasi")
                score -= 1.5
            elif macd_trend == "WEAKENING_BEAR":
                reasons.append("MACD: bearish tapi momentum mulai melemah")
                score += 0.5
            elif macd_trend == "WEAKENING_BULL":
                reasons.append("MACD: bullish tapi momentum mulai melemah")
                score -= 0.5

    except Exception as e:
        reasons.append(f"Indikator teknikal tidak tersedia: {e}")

    # ── 3. Fear & Greed ────────────────────────────────────
    if fear_greed is not None:
        if fear_greed <= 25:
            reasons.append(f"Fear & Greed {fear_greed} = Extreme Fear — historis bagus untuk akumulasi")
            score += 1.5
        elif fear_greed <= 40:
            reasons.append(f"Fear & Greed {fear_greed} = Fear — sentimen negatif, bisa jadi peluang")
            score += 0.5
        elif fear_greed >= 80:
            reasons.append(f"Fear & Greed {fear_greed} = Extreme Greed — risiko tinggi, banyak FOMO")
            score -= 1.5
        elif fear_greed >= 65:
            reasons.append(f"Fear & Greed {fear_greed} = Greed — pasar optimis, waspadai koreksi")
            score -= 0.5
        else:
            reasons.append(f"Fear & Greed {fear_greed} = Neutral")

    # ── 4. Tentukan sinyal final ───────────────────────────
    if score >= 3:
        signal_type, strength = "BUY", "STRONG"
    elif score >= 1.5:
        signal_type, strength = "BUY", "MODERATE"
    elif score >= 0.5:
        signal_type, strength = "WATCH", "MODERATE"
    elif score <= -3:
        signal_type, strength = "SELL", "STRONG"
    elif score <= -1.5:
        signal_type, strength = "SELL", "MODERATE"
    elif score <= -0.5:
        signal_type, strength = "WATCH", "WEAK"
    else:
        signal_type, strength = "HOLD", "WEAK"
        if not any("stabil" in r for r in reasons):
            reasons.append("Belum ada sinyal kuat — disarankan hold")

    return Signal(
        coin=coin,
        price=price,
        change_24h=change,
        signal_type=signal_type,
        strength=strength,
        reasons=reasons,
        rsi=rsi_val,
        macd_trend=macd_trend,
        fear_greed=fear_greed,
    )


def should_notify(signal: Signal) -> bool:
    """Kirim notif Telegram hanya untuk sinyal yang cukup kuat."""
    if signal.signal_type in ("BUY", "SELL") and signal.strength in ("STRONG", "MODERATE"):
        return True
    if abs(signal.change_24h) >= 8:
        return True
    return False
