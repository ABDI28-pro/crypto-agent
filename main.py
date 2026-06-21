"""
main.py — Entry point untuk deployment cloud.

Menjalankan 2 proses sekaligus dalam 1 worker:
  1. telegram_agent.py  — bot interaktif, respon real-time ke pesan user
  2. scheduler.py       — scan otomatis tiap jam, kirim sinyal proaktif

Kenapa digabung jadi 1 file:
  Platform gratis seperti Railway/Render biasanya kasih 1 process/service
  di free tier. Daripada deploy 2 service terpisah (butuh paid plan),
  kita jalankan keduanya sebagai thread di proses yang sama.
"""

import threading
import time
import sys

def run_telegram_bot():
    """Thread 1: bot interaktif Telegram."""
    print("[main] Starting Telegram interactive bot...")
    try:
        from telegram_agent import main as telegram_main
        telegram_main()
    except Exception as e:
        print(f"[main] Telegram bot crashed: {e}")


def run_scheduler():
    """Thread 2: scheduler otomatis untuk sinyal proaktif."""
    print("[main] Starting scheduler...")
    time.sleep(5)  # beri jeda supaya tidak fetch bersamaan saat startup
    try:
        from scheduler import main as scheduler_main
        sys.argv = ["scheduler.py"]  # mode loop normal, bukan --once/--test
        scheduler_main()
    except Exception as e:
        print(f"[main] Scheduler crashed: {e}")


if __name__ == "__main__":
    print("=" * 55)
    print("  Crypto Intelligence Agent — Cloud Worker")
    print("  Menjalankan: Telegram Bot + Scheduler")
    print("=" * 55)

    telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)

    telegram_thread.start()
    scheduler_thread.start()

    # Keep main process alive
    try:
        while True:
            time.sleep(60)
            # Restart thread kalau crash
            if not telegram_thread.is_alive():
                print("[main] Telegram bot thread mati, restart...")
                telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
                telegram_thread.start()
            if not scheduler_thread.is_alive():
                print("[main] Scheduler thread mati, restart...")
                scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
                scheduler_thread.start()
    except KeyboardInterrupt:
        print("\n[main] Dihentikan.")
