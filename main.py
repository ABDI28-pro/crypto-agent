"""
main.py — Entry point untuk deployment Render (Web Service).

Render free tier butuh service yang listen di sebuah PORT (HTTP),
kalau tidak dia anggap "bukan web service" dan deployment gagal start.

Strategi:
  1. Flask app kecil yang listen di PORT — bikin Render senang
  2. Endpoint "/" untuk health check (dan keep-alive ping dari luar)
  3. Telegram bot + scheduler jalan di background thread terpisah

Auto-sleep Render: kalau tidak ada HTTP request selama 15 menit, service
tidur. Untuk tetap hidup 24 jam, pakai UptimeRobot (gratis) untuk ping
endpoint "/" setiap 5 menit — lihat instruksi di README.
"""

import threading
import time
import sys
import os
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

START_TIME = datetime.now()
LAST_PING = {"time": None}


@app.route("/")
def health_check():
    """Endpoint untuk Render health check + keep-alive ping dari UptimeRobot."""
    LAST_PING["time"] = datetime.now().isoformat()
    uptime = datetime.now() - START_TIME
    return jsonify({
        "status": "alive",
        "service": "Crypto Intelligence Agent",
        "uptime_seconds": int(uptime.total_seconds()),
        "last_ping": LAST_PING["time"],
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


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
    time.sleep(8)
    try:
        from scheduler import main as scheduler_main
        sys.argv = ["scheduler.py"]
        scheduler_main()
    except Exception as e:
        print(f"[main] Scheduler crashed: {e}")


def start_background_workers():
    """Mulai Telegram bot + scheduler sebagai daemon thread."""
    telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    telegram_thread.start()
    scheduler_thread.start()

    def watchdog():
        nonlocal telegram_thread, scheduler_thread
        while True:
            time.sleep(60)
            if not telegram_thread.is_alive():
                print("[main] Telegram bot mati, restart...")
                telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
                telegram_thread.start()
            if not scheduler_thread.is_alive():
                print("[main] Scheduler mati, restart...")
                scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
                scheduler_thread.start()

    watchdog_thread = threading.Thread(target=watchdog, daemon=True)
    watchdog_thread.start()


if __name__ == "__main__":
    print("=" * 55)
    print("  Crypto Intelligence Agent — Render Web Service")
    print("  Telegram Bot + Scheduler + Health Check endpoint")
    print("=" * 55)

    start_background_workers()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
