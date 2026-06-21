"""
agents/analysis_agent.py — Analysis Agent.

Tanggung jawab TUNGGAL: terima data mentah dari DataAgent,
hasilkan sinyal trading (LONG/SHORT/WAIT) dengan confidence score.

Agent ini TIDAK fetch data sendiri — dia hanya menganalisis
data yang sudah dikumpulkan DataAgent. Pemisahan ini membuat
logika analisis bisa di-test dengan data palsu (mock) tanpa internet.
"""

from dataclasses import dataclass


@dataclass
class AnalysisResult:
    coin: str
    signal: str           # LONG, SHORT, WAIT
    confidence: int        # 0-100
    entry_price: float
    tp1: float
    tp2: float
    stop_loss: float
    reasons: list
    raw_scores: dict       # long_score, short_score untuk transparansi


class AnalysisAgent:
    """Agent yang menganalisis data mentah jadi sinyal trading."""

    name = "AnalysisAgent"

    def analyze(self, gathered_data: dict) -> AnalysisResult:
        """
        Analisis data dari DataAgent, hasilkan sinyal.
        """
        if "error" in gathered_data:
            return None

        print(f"  [{self.name}] Menganalisis {gathered_data['coin'].upper()}...")

        ind = gathered_data.get("indicators", {})
        if not ind:
            return None

        price = ind["price"]
        reasons = []
        long_score = 0
        short_score = 0

        # RSI
        rsi = ind.get("rsi", 50)
        if rsi < 30:
            reasons.append(f"RSI {rsi} oversold")
            long_score += 25
        elif rsi > 70:
            reasons.append(f"RSI {rsi} overbought")
            short_score += 25

        # MACD
        macd_line = ind.get("macd_line", 0)
        signal_line = ind.get("signal_line", 0)
        if macd_line > signal_line:
            reasons.append("MACD bullish")
            long_score += 15
        else:
            reasons.append("MACD bearish")
            short_score += 15

        # Bollinger Bands
        bb_pct = ind.get("bb_pct", 0.5)
        if bb_pct < 0.1:
            reasons.append("Harga di lower BB")
            long_score += 12
        elif bb_pct > 0.9:
            reasons.append("Harga di upper BB")
            short_score += 12

        # Multi-timeframe confluence
        mtf = gathered_data.get("multi_timeframe", {})
        mtf_confluence = mtf.get("confluence", "UNKNOWN")
        mtf_score = mtf.get("confluence_score", 0)

        if mtf_confluence == "BULLISH":
            bonus = mtf_score * 8
            long_score += bonus
            reasons.append(f"MTF bullish ({mtf_score}/3 timeframe)")
        elif mtf_confluence == "BEARISH":
            bonus = mtf_score * 8
            short_score += bonus
            reasons.append(f"MTF bearish ({mtf_score}/3 timeframe)")

        # Fear & Greed
        fg = gathered_data.get("fear_greed")
        if fg is not None:
            if fg <= 25:
                long_score += 10
                reasons.append(f"F&G {fg} extreme fear")
            elif fg >= 75:
                short_score += 10
                reasons.append(f"F&G {fg} extreme greed")

        # Tentukan sinyal
        total = long_score + short_score
        atr = ind.get("atr", price * 0.02)
        sr = gathered_data.get("support_resistance", {})

        if long_score > short_score and long_score >= 45:
            signal = "LONG"
            confidence = min(int(long_score / max(total, 1) * 100), 97)
            entry = price
            sl = sr.get("nearest_support", entry - atr * 1.5) if sr.get("nearest_support") else entry - atr * 1.5
            tp1 = sr.get("nearest_resistance", entry + atr * 1.5) if sr.get("nearest_resistance") else entry + atr * 1.5
            tp2 = entry + atr * 3
        elif short_score > long_score and short_score >= 45:
            signal = "SHORT"
            confidence = min(int(short_score / max(total, 1) * 100), 97)
            entry = price
            sl = sr.get("nearest_resistance", entry + atr * 1.5) if sr.get("nearest_resistance") else entry + atr * 1.5
            tp1 = sr.get("nearest_support", entry - atr * 1.5) if sr.get("nearest_support") else entry - atr * 1.5
            tp2 = entry - atr * 3
        else:
            signal = "WAIT"
            confidence = 0
            entry = price
            sl = price * 0.98
            tp1 = price * 1.02
            tp2 = price * 1.04
            reasons.append("Sinyal belum cukup kuat")

        return AnalysisResult(
            coin=gathered_data["coin"], signal=signal, confidence=confidence,
            entry_price=round(entry, 6), tp1=round(tp1, 6), tp2=round(tp2, 6),
            stop_loss=round(sl, 6), reasons=reasons,
            raw_scores={"long": long_score, "short": short_score},
        )
