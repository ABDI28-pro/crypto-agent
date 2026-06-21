"""
telegram_agent.py — Bot Telegram interaktif + whale tracker + price alert + scalping.

Cara jalankan:
  python telegram_agent.py

Commands di Telegram:
  /start    — Sapa bot
  /help     — Daftar semua command
  /market   — Overview market
  /btc /eth /sol /bnb /xrp /doge — Analisis koin
  /scalp btc — Sinyal scalping (RSI+MACD+BB+EMA+Volume+F&G)
  /whale    — Cek transaksi whale terbaru
  /alerts   — Lihat price alert aktif
  /addalert bitcoin above 100000 BTC 6 digit! — Tambah alert
  /fng      — Fear & Greed Index
  /trending — Koin trending
  Atau tanya apa saja dalam bahasa bebas!
"""

import os
import time
import requests
from dotenv import load_dotenv
from agent import ask_agent
from whale_tracker import check_whale_activity
from price_alert import check_all_alerts, add_alert, list_alerts, remove_alert
from scalping_engine import analyze_scalp
from scalping_bot import format_signal_telegram
from tools import get_fear_and_greed
from whale_tracker_v2 import scan_whale_activity, format_whale_report

load_dotenv()

TELEGRAM_API = "https://api.telegram.org"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
POLL_INTERVAL = 2


def get_updates(offset=None) -> list:
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    try:
        r = requests.get(
            f"{TELEGRAM_API}/bot{TOKEN}/getUpdates",
            params=params, timeout=35,
        )
        r.raise_for_status()
        return r.json().get("result", [])
    except Exception as e:
        print(f"  [poll error] {e}")
        return []


def reply(chat_id: int, text: str):
    try:
        if len(text) > 4000:
            text = text[:4000] + "\n...(dipotong)"
        requests.post(
            f"{TELEGRAM_API}/bot{TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"  [reply error] {e}")


def typing(chat_id: int):
    try:
        requests.post(
            f"{TELEGRAM_API}/bot{TOKEN}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"}, timeout=5,
        )
    except Exception:
        pass


def handle_message(chat_id: int, text: str, histories: dict):
    text = text.strip()
    cmd = text.lower().split()[0] if text else ""
    print(f"  [msg] {chat_id}: {text[:60]}")

    if cmd in ("/start", "halo", "hai", "hello"):
        reply(chat_id, (
            "👋 <b>Halo! Saya Super Crypto Intelligence Agent.</b>\n\n"
            "Fitur yang tersedia:\n"
            "📊 Analisis harga real-time\n"
            "🎯 Sinyal scalping (RSI+MACD+BB+EMA+Volume)\n"
            "🐋 Whale transaction tracker\n"
            "🔔 Price alert otomatis\n\n"
            "Ketik /help untuk daftar lengkap command.\n"
            "Atau langsung tanya apa saja!"
        ))
        return

    if cmd == "/scalp":
        typing(chat_id)
        parts = text.split()
        coin = parts[1].lower() if len(parts) > 1 else "bitcoin"
        reply(chat_id, f"Menganalisis sinyal scalping {coin.upper()}...")

        fg = get_fear_and_greed()
        fg_val = fg.get("value") if "error" not in fg else None

        sig = analyze_scalp(coin, fg_val)
        if sig:
            reply(chat_id, format_signal_telegram(sig))
        else:
            reply(chat_id, f"Gagal analisis {coin}. Coba nama koin lain, contoh: /scalp eth")
        return

    if cmd == "/help":
        reply(chat_id, (
            "📚 <b>Daftar Command</b>\n\n"
            "<b>Market:</b>\n"
            "/market — Overview market hari ini\n"
            "/fng — Fear &amp; Greed Index\n"
            "/trending — Koin trending\n\n"
            "<b>Analisis Koin:</b>\n"
            "/btc /eth /sol /bnb /xrp /doge\n"
            "/ada /avax /dot /link\n\n"
            "<b>Scalping Signal:</b>\n"
            "/scalp btc — Sinyal scalping Bitcoin\n"
            "/scalp eth — Sinyal scalping Ethereum\n"
            "(Entry, TP1, TP2, SL, R/R otomatis)\n\n"
            "<b>Whale Tracker:</b>\n"
            "/whale — Transaksi whale terbaru ($1M+)\n"
            "/whale 5000000 — Min $5 juta\n"
            "/whale2 — Super tracker ETH+BSC (deposit/withdraw exchange)\n\n"
            "<b>Price Alert:</b>\n"
            "/alerts — Lihat semua alert aktif\n"
            "/addalert bitcoin above 100000 BTC ATH!\n"
            "/addalert ethereum below 1500 ETH murah\n"
            "/removealert bitcoin 1 — Hapus alert #1\n\n"
            "<b>Lainnya:</b>\n"
            "/reset — Hapus riwayat chat\n\n"
            "Atau ketik pertanyaan bebas dalam bahasa Indonesia!"
        ))
        return

    if cmd == "/reset":
        histories[chat_id] = []
        reply(chat_id, "🔄 Riwayat percakapan dihapus!")
        return

    if cmd == "/whale2":
        typing(chat_id)
        reply(chat_id, "🐋 Scanning whale activity di Ethereum + BSC...")
        result = scan_whale_activity()
        reply(chat_id, format_whale_report(result))
        return

    if cmd == "/whale":
        typing(chat_id)
        parts = text.split()
        min_usd = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1_000_000
        reply(chat_id, f"🐋 Mengambil transaksi whale (min ${min_usd:,})...")
        result = check_whale_activity(min_usd)
        reply(chat_id, result["summary"])
        return

    if cmd == "/alerts":
        reply(chat_id, list_alerts())
        return

    if cmd == "/addalert":
        parts = text.split(maxsplit=4)
        if len(parts) < 4:
            reply(chat_id, (
                "Format: /addalert &lt;coin&gt; &lt;above|below&gt; &lt;price&gt; [catatan]\n\n"
                "Contoh:\n"
                "/addalert bitcoin above 100000 BTC ATH!\n"
                "/addalert ethereum below 1500 ETH murah nih"
            ))
            return
        coin = parts[1].lower()
        direction = parts[2].lower()
        try:
            price = float(parts[3].replace(",", ""))
        except ValueError:
            reply(chat_id, "Harga tidak valid. Contoh: /addalert bitcoin above 100000")
            return
        note = parts[4] if len(parts) > 4 else ""
        if direction not in ("above", "below"):
            reply(chat_id, "Gunakan 'above' (di atas) atau 'below' (di bawah)")
            return
        add_alert(coin, direction, price, note)
        arrow = "▲" if direction == "above" else "▼"
        reply(chat_id, f"✅ Alert ditambahkan!\n{coin.upper()} {arrow} ${price:,.0f}\n{note}")
        return

    if cmd == "/removealert":
        parts = text.split()
        if len(parts) < 3:
            reply(chat_id, "Format: /removealert &lt;coin&gt; &lt;nomor&gt;\nContoh: /removealert bitcoin 1")
            return
        coin = parts[1].lower()
        try:
            idx = int(parts[2]) - 1
        except ValueError:
            reply(chat_id, "Nomor tidak valid.")
            return
        if remove_alert(coin, idx):
            reply(chat_id, f"✅ Alert {coin.upper()} #{idx+1} dihapus.")
        else:
            reply(chat_id, "Alert tidak ditemukan.")
        return

    shortcuts = {
        "/market":   "Bagaimana kondisi market crypto hari ini? Cek overview dan fear greed index.",
        "/fng":      "Berapa Fear and Greed Index hari ini? Apa artinya untuk market?",
        "/trending": "Koin apa saja yang sedang trending hari ini? Layak diperhatikan?",
        "/btc":      "Analisis lengkap Bitcoin: harga, perubahan 24 jam, RSI, MACD, rekomendasi.",
        "/eth":      "Analisis lengkap Ethereum: harga, perubahan 24 jam, RSI, MACD, rekomendasi.",
        "/sol":      "Analisis lengkap Solana: harga, perubahan 24 jam, RSI, MACD, rekomendasi.",
        "/bnb":      "Analisis lengkap BNB: harga, perubahan 24 jam, RSI, MACD, rekomendasi.",
        "/xrp":      "Analisis lengkap XRP Ripple: harga, perubahan 24 jam, RSI, MACD, rekomendasi.",
        "/doge":     "Analisis lengkap Dogecoin: harga, perubahan 24 jam, RSI, MACD, rekomendasi.",
        "/ada":      "Analisis lengkap Cardano ADA: harga, perubahan 24 jam, RSI, MACD, rekomendasi.",
        "/avax":     "Analisis lengkap Avalanche AVAX: harga, RSI, MACD, rekomendasi.",
        "/dot":      "Analisis lengkap Polkadot DOT: harga, RSI, MACD, rekomendasi.",
        "/link":     "Analisis lengkap Chainlink LINK: harga, RSI, MACD, rekomendasi.",
    }

    question = shortcuts.get(cmd, text)

    if chat_id not in histories:
        histories[chat_id] = []
    typing(chat_id)

    try:
        answer, new_history = ask_agent(question, histories[chat_id])
        histories[chat_id] = new_history[-20:]
        reply(chat_id, answer)
    except Exception as e:
        print(f"  [agent error] {e}")
        reply(chat_id, f"⚠️ Error: {str(e)[:200]}")


def main():
    if not TOKEN or "xxx" in TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN belum diset di .env")
        return

    print("=" * 55)
    print("  Crypto Agent — Telegram Interactive Bot")
    print("  Fitur: Chat AI + Scalping + Whale Tracker + Alert")
    print("  Buka Telegram → chat bot → tanya apa saja!")
    print("  Ctrl+C untuk berhenti")
    print("=" * 55)

    histories = {}
    offset = None
    check_count = 0

    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "").strip()
                chat_id = msg.get("chat", {}).get("id")
                if text and chat_id:
                    handle_message(chat_id, text, histories)

            check_count += 1
            if check_count % 150 == 0:
                triggered = check_all_alerts()
                if triggered:
                    print(f"  [alert] {len(triggered)} price alert triggered")

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\nBot dihentikan.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
