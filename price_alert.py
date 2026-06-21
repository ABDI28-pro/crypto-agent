"""
price_alert.py — Alert harga otomatis.

Cara pakai:
  - Set target harga di alerts.json
  - Setiap cek, kalau harga tembus target → notif Telegram

Format alerts.json:
  {
    "bitcoin": [
      {"type": "above", "price": 100000, "note": "ATH breakout!"},
      {"type": "below", "price": 80000,  "note": "Support kuat"}
    ],
    "ethereum": [
      {"type": "above", "price": 4000, "note": "Target profit"}
    ]
  }
"""

import json
import os
from datetime import datetime
from tools import get_crypto_price
from telegram_bot import send_message

ALERTS_FILE = "alerts.json"
TRIGGERED_FILE = "triggered_alerts.json"


def load_alerts() -> dict:
    """Load konfigurasi alert dari file JSON."""
    if not os.path.exists(ALERTS_FILE):
        # Buat file contoh kalau belum ada
        default = {
            "bitcoin": [
                {"type": "above", "price": 100000, "note": "BTC 6 digit!"},
                {"type": "below", "price": 50000,  "note": "BTC support kuat"}
            ],
            "ethereum": [
                {"type": "above", "price": 4000, "note": "ETH target"},
                {"type": "below", "price": 1500, "note": "ETH murah"}
            ],
            "solana": [
                {"type": "above", "price": 200, "note": "SOL ATH zone"},
                {"type": "below", "price": 50,  "note": "SOL oversold"}
            ]
        }
        save_alerts(default)
        return default
    with open(ALERTS_FILE) as f:
        return json.load(f)


def save_alerts(alerts: dict):
    """Simpan alert ke file."""
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


def load_triggered() -> set:
    """Load daftar alert yang sudah pernah triggered (hindari spam)."""
    if not os.path.exists(TRIGGERED_FILE):
        return set()
    with open(TRIGGERED_FILE) as f:
        return set(json.load(f))


def save_triggered(triggered: set):
    """Simpan daftar alert yang sudah triggered."""
    with open(TRIGGERED_FILE, "w") as f:
        json.dump(list(triggered), f)


def add_alert(coin: str, alert_type: str, price: float, note: str = "") -> bool:
    """
    Tambah alert baru.

    Args:
        coin       : nama koin (bitcoin, ethereum, dll)
        alert_type : 'above' atau 'below'
        price      : target harga dalam USD
        note       : catatan opsional

    Returns:
        True kalau berhasil ditambah
    """
    alerts = load_alerts()
    if coin not in alerts:
        alerts[coin] = []

    new_alert = {"type": alert_type, "price": price, "note": note}
    alerts[coin].append(new_alert)
    save_alerts(alerts)
    return True


def remove_alert(coin: str, index: int) -> bool:
    """Hapus alert berdasarkan index."""
    alerts = load_alerts()
    if coin not in alerts or index >= len(alerts[coin]):
        return False
    alerts[coin].pop(index)
    save_alerts(alerts)
    return True


def check_all_alerts() -> list:
    """
    Cek semua alert, kirim notif Telegram kalau ada yang triggered.
    Return list alert yang triggered.
    """
    alerts = load_alerts()
    triggered_keys = load_triggered()
    newly_triggered = []

    for coin, coin_alerts in alerts.items():
        if not coin_alerts:
            continue

        price_data = get_crypto_price(coin)
        if "error" in price_data:
            continue

        current_price = price_data["price_usd"]

        for i, alert in enumerate(coin_alerts):
            alert_key = f"{coin}_{alert['type']}_{alert['price']}"

            target = alert["price"]
            alert_type = alert["type"]
            note = alert.get("note", "")

            triggered = (
                (alert_type == "above" and current_price >= target) or
                (alert_type == "below" and current_price <= target)
            )

            if triggered and alert_key not in triggered_keys:
                # Kirim notif
                direction = "naik melewati" if alert_type == "above" else "turun ke bawah"
                emoji = "🚀" if alert_type == "above" else "⚠️"
                change = price_data.get("change_24h_pct", 0)
                change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"

                msg = (
                    f"{emoji} <b>PRICE ALERT — {coin.upper()}</b>\n\n"
                    f"Harga <b>{direction}</b> target ${target:,.0f}\n"
                    f"Harga sekarang: <b>${current_price:,.2f}</b> ({change_str})\n"
                )
                if note:
                    msg += f"\nCatatan: {note}"
                msg += "\n\n<i>— Crypto Intelligence Agent</i>"

                result = send_message(msg)
                if "success" in result:
                    triggered_keys.add(alert_key)
                    newly_triggered.append({
                        "coin": coin,
                        "alert": alert,
                        "current_price": current_price,
                    })
                    print(f"  ALERT: {coin.upper()} {alert_type} ${target:,} → harga sekarang ${current_price:,.2f}")

            elif not triggered and alert_key in triggered_keys:
                # Reset kalau harga kembali normal (bisa trigger lagi nanti)
                triggered_keys.discard(alert_key)

    save_triggered(triggered_keys)
    return newly_triggered


def list_alerts() -> str:
    """Format semua alert jadi teks yang bisa dibaca."""
    alerts = load_alerts()
    if not alerts:
        return "Belum ada alert yang diset."

    lines = ["📋 <b>Daftar Price Alert</b>\n"]
    for coin, coin_alerts in alerts.items():
        if not coin_alerts:
            continue
        lines.append(f"<b>{coin.upper()}</b>")
        for i, a in enumerate(coin_alerts):
            direction = "▲ di atas" if a["type"] == "above" else "▼ di bawah"
            note = f" — {a['note']}" if a.get("note") else ""
            lines.append(f"  {i+1}. {direction} ${a['price']:,}{note}")
    return "\n".join(lines)
