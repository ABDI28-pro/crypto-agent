"""
agents/orchestrator.py — Orchestrator Agent.

Tanggung jawab: koordinasi DataAgent → AnalysisAgent → RiskAgent
jadi satu pipeline lengkap. Ini "supervisor" yang mengatur alur kerja
antar agent dan menghasilkan output akhir yang siap dipakai user.

Pipeline:
  1. DataAgent     → kumpulkan semua data mentah
  2. AnalysisAgent → hasilkan sinyal trading dari data tersebut
  3. RiskAgent     → validasi sinyal, approve/reject, hitung position size
  4. Orchestrator  → gabungkan semua jadi laporan akhir
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.data_agent import DataAgent
from agents.analysis_agent import AnalysisAgent
from agents.risk_agent import RiskAssessment, RiskAgent


class TradingOrchestrator:
    """Koordinator utama — jalankan pipeline 3 agent secara berurutan."""

    name = "Orchestrator"

    def __init__(self):
        self.data_agent = DataAgent()
        self.analysis_agent = AnalysisAgent()
        self.risk_agent = RiskAgent()

    def process(self, coin: str) -> dict:
        """
        Jalankan pipeline lengkap untuk satu koin.

        Returns:
            dict dengan keys: coin, data, analysis, risk, final_recommendation
        """
        print(f"\n[{self.name}] Memulai pipeline untuk {coin.upper()}")
        print(f"{'='*55}")

        # ── Step 1: Data Agent ───────────────────────────────
        data = self.data_agent.gather(coin)
        if "error" in data:
            return {
                "coin": coin,
                "status": "ERROR",
                "message": f"DataAgent gagal: {data['error']}",
            }

        # ── Step 2: Analysis Agent ───────────────────────────
        analysis = self.analysis_agent.analyze(data)
        if analysis is None:
            return {
                "coin": coin,
                "status": "ERROR",
                "message": "AnalysisAgent gagal — data tidak cukup untuk analisis",
            }

        # ── Step 3: Risk Agent ────────────────────────────────
        fg = data.get("fear_greed")
        risk = self.risk_agent.assess(analysis, fear_greed=fg)

        # ── Step 4: Gabungkan jadi rekomendasi final ─────────
        final_recommendation = self._build_recommendation(coin, analysis, risk, data)

        print(f"{'='*55}")
        print(f"[{self.name}] Pipeline selesai — status: {final_recommendation['status']}")

        return {
            "coin": coin,
            "status": "OK",
            "data": data,
            "analysis": analysis,
            "risk": risk,
            "final_recommendation": final_recommendation,
        }

    def _build_recommendation(self, coin: str, analysis, risk: RiskAssessment, data: dict) -> dict:
        """Gabungkan hasil semua agent jadi rekomendasi yang mudah dibaca."""
        if not risk.approved:
            return {
                "status": "REJECTED",
                "signal": analysis.signal,
                "reason": risk.rejection_reason,
                "raw_confidence": analysis.confidence,
            }

        return {
            "status": "APPROVED",
            "signal": analysis.signal,
            "confidence": analysis.confidence,
            "entry": analysis.entry_price,
            "tp1": analysis.tp1,
            "tp2": analysis.tp2,
            "stop_loss": analysis.stop_loss,
            "rr_ratio": risk.rr_ratio,
            "suggested_position_pct": risk.position_size_pct,
            "warnings": risk.warnings,
            "reasons": analysis.reasons,
        }

    def format_report(self, result: dict) -> str:
        """Format hasil pipeline jadi teks yang bisa dibaca user."""
        if result["status"] == "ERROR":
            return f"❌ Error: {result['message']}"

        rec = result["final_recommendation"]
        coin = result["coin"].upper()

        if rec["status"] == "REJECTED":
            return (
                f"⚪ <b>{coin} — Sinyal Ditolak</b>\n\n"
                f"Sinyal mentah: {rec['signal']} (confidence {rec['raw_confidence']}%)\n"
                f"Alasan ditolak: {rec['reason']}\n\n"
                f"<i>Risk Agent menolak sinyal ini karena tidak memenuhi standar risk management.</i>"
            )

        emoji = "🟢" if rec["signal"] == "LONG" else "🔴"
        warnings_text = ""
        if rec["warnings"]:
            warnings_text = "\n\n⚠️ <b>Peringatan:</b>\n" + "\n".join(f"• {w}" for w in rec["warnings"])

        reasons_text = "\n".join(f"• {r}" for r in rec["reasons"])

        return (
            f"{emoji} <b>{coin} — {rec['signal']} APPROVED</b>\n"
            f"Confidence: {rec['confidence']}%\n\n"
            f"<b>Entry:</b> ${rec['entry']:,.4f}\n"
            f"<b>TP1:</b> ${rec['tp1']:,.4f}\n"
            f"<b>TP2:</b> ${rec['tp2']:,.4f}\n"
            f"<b>SL:</b> ${rec['stop_loss']:,.4f}\n"
            f"<b>R/R:</b> 1:{rec['rr_ratio']}\n"
            f"<b>Saran position size:</b> {rec['suggested_position_pct']}% dari modal\n"
            f"{warnings_text}\n\n"
            f"<b>Analisis (3 agent):</b>\n{reasons_text}\n\n"
            f"<i>Diproses oleh: DataAgent → AnalysisAgent → RiskAgent</i>"
        )

    def process_multiple(self, coins: list) -> list:
        """Jalankan pipeline untuk beberapa koin, return hanya yang APPROVED."""
        approved_results = []
        for coin in coins:
            result = self.process(coin)
            if result["status"] == "OK" and result["final_recommendation"]["status"] == "APPROVED":
                approved_results.append(result)
        return approved_results
