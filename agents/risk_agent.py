"""
agents/risk_agent.py — Risk Management Agent.

Tanggung jawab TUNGGAL: validasi sinyal dari AnalysisAgent terhadap
aturan risk management. Bisa MENOLAK sinyal yang secara teknis valid
tapi terlalu berisiko untuk dieksekusi.

Ini agent paling penting dalam sistem trading — dia "rem" yang
mencegah overtrading dan posisi yang risk/reward-nya jelek.
"""

from dataclasses import dataclass


@dataclass
class RiskAssessment:
    approved: bool
    risk_pct: float
    reward_pct: float
    rr_ratio: float
    position_size_pct: float   # saran ukuran posisi sebagai % dari modal
    warnings: list
    rejection_reason: str = None


class RiskAgent:
    """Agent yang validasi sinyal terhadap aturan risk management."""

    name = "RiskAgent"

    # Aturan risk management — bisa di-tune sesuai toleransi risiko
    MIN_CONFIDENCE = 55          # tolak sinyal di bawah confidence ini
    MIN_RR_RATIO = 1.2           # tolak kalau risk/reward kurang dari ini
    MAX_RISK_PCT = 3.0           # tolak kalau risk terlalu jauh dari entry (>3%)
    MAX_POSITION_PCT = 5.0       # saran maksimal ukuran posisi per trade

    def assess(self, analysis_result, fear_greed: int = None) -> RiskAssessment:
        """
        Validasi hasil AnalysisAgent. Bisa approve atau reject.
        """
        if analysis_result is None or analysis_result.signal == "WAIT":
            return RiskAssessment(
                approved=False, risk_pct=0, reward_pct=0, rr_ratio=0,
                position_size_pct=0, warnings=[],
                rejection_reason="Tidak ada sinyal aktif (WAIT)",
            )

        print(f"  [{self.name}] Validasi sinyal {analysis_result.signal} {analysis_result.coin.upper()}...")

        entry = analysis_result.entry_price
        sl = analysis_result.stop_loss
        tp1 = analysis_result.tp1

        risk_pct = abs(entry - sl) / entry * 100
        reward_pct = abs(tp1 - entry) / entry * 100
        rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0

        warnings = []

        # ── Rule 1: Minimum confidence ──────────────────────
        if analysis_result.confidence < self.MIN_CONFIDENCE:
            return RiskAssessment(
                approved=False, risk_pct=risk_pct, reward_pct=reward_pct,
                rr_ratio=round(rr_ratio, 2), position_size_pct=0, warnings=warnings,
                rejection_reason=f"Confidence {analysis_result.confidence}% di bawah minimum {self.MIN_CONFIDENCE}%",
            )

        # ── Rule 2: Minimum R/R ratio ────────────────────────
        if rr_ratio < self.MIN_RR_RATIO:
            return RiskAssessment(
                approved=False, risk_pct=risk_pct, reward_pct=reward_pct,
                rr_ratio=round(rr_ratio, 2), position_size_pct=0, warnings=warnings,
                rejection_reason=f"R/R ratio 1:{rr_ratio:.1f} di bawah minimum 1:{self.MIN_RR_RATIO}",
            )

        # ── Rule 3: Risk terlalu besar ───────────────────────
        if risk_pct > self.MAX_RISK_PCT:
            return RiskAssessment(
                approved=False, risk_pct=risk_pct, reward_pct=reward_pct,
                rr_ratio=round(rr_ratio, 2), position_size_pct=0, warnings=warnings,
                rejection_reason=f"Risk {risk_pct:.1f}% terlalu besar (max {self.MAX_RISK_PCT}%) — SL terlalu jauh dari entry",
            )

        # ── Warning: Extreme Greed (risiko reversal tinggi) ──
        if fear_greed is not None and fear_greed >= 80 and analysis_result.signal == "LONG":
            warnings.append("Fear&Greed extreme greed — LONG di sini berisiko tinggi reversal")

        if fear_greed is not None and fear_greed <= 15 and analysis_result.signal == "SHORT":
            warnings.append("Fear&Greed extreme fear — SHORT di sini berisiko tinggi bounce")

        # ── Hitung saran position size berdasarkan confidence ──
        # Confidence tinggi + R/R bagus = position size lebih besar (tapi tetap dibatasi MAX)
        confidence_factor = analysis_result.confidence / 100
        rr_factor = min(rr_ratio / 2, 1.5)
        position_size = round(self.MAX_POSITION_PCT * confidence_factor * rr_factor / 1.5, 2)
        position_size = min(position_size, self.MAX_POSITION_PCT)

        return RiskAssessment(
            approved=True,
            risk_pct=round(risk_pct, 2),
            reward_pct=round(reward_pct, 2),
            rr_ratio=round(rr_ratio, 2),
            position_size_pct=position_size,
            warnings=warnings,
        )
