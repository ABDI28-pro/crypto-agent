"""
run_agents.py — CLI untuk menjalankan Multi-Agent Trading Pipeline.

Arsitektur:
  DataAgent → AnalysisAgent → RiskAgent → Orchestrator

Setiap agent punya tanggung jawab tunggal dan bisa di-test terpisah.
Orchestrator mengatur alur kerja dan menggabungkan hasil akhir.

Cara pakai:
  python run_agents.py --coin btc                 → jalankan pipeline untuk 1 koin
  python run_agents.py --coins btc eth sol bnb     → scan banyak koin, tampilkan yang approved
  python run_agents.py --coin btc --telegram       → kirim hasil ke Telegram juga
"""

import argparse
from agents.orchestrator import TradingOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Crypto Trading Pipeline")
    parser.add_argument("--coin", type=str, help="Proses 1 koin: --coin btc")
    parser.add_argument("--coins", nargs="+", help="Proses banyak koin: --coins btc eth sol")
    parser.add_argument("--telegram", action="store_true", help="Kirim hasil approved ke Telegram")
    args = parser.parse_args()

    print("=" * 55)
    print("  Multi-Agent Crypto Trading Pipeline")
    print("  DataAgent → AnalysisAgent → RiskAgent")
    print("=" * 55)

    orchestrator = TradingOrchestrator()

    if args.coin:
        result = orchestrator.process(args.coin)
        report = orchestrator.format_report(result)
        print("\n" + report.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""))

        if args.telegram and result["status"] == "OK" and result["final_recommendation"]["status"] == "APPROVED":
            from telegram_bot import send_message
            send_message(report)
            print("\n[Terkirim ke Telegram]")

    elif args.coins:
        print(f"\nMemproses {len(args.coins)} koin...\n")
        approved = orchestrator.process_multiple(args.coins)

        print(f"\n{'='*55}")
        print(f"  HASIL: {len(approved)} dari {len(args.coins)} koin APPROVED")
        print(f"{'='*55}\n")

        for result in approved:
            report = orchestrator.format_report(result)
            clean_report = report.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
            print(clean_report)
            print("-" * 55)

            if args.telegram:
                from telegram_bot import send_message
                send_message(report)

        if args.telegram and approved:
            print(f"\n[{len(approved)} sinyal terkirim ke Telegram]")

    else:
        print("\nGunakan --coin <nama> atau --coins <nama1> <nama2> ...")
        print("Contoh: python run_agents.py --coin btc")


if __name__ == "__main__":
    main()
