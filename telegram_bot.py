"""
telegram_bot.py — Kirim pesan dan sinyal ke Telegram.
Sekarang format sinyal include RSI + MACD.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_API = "https://api.telegram.org"


def send_message(text: str, parse_mode: str = "HTML") -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id or "xxx" in token:
        return {"error": "TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum diset di .env"}
    try:
        r = requests.post(
            f"{TELEGRAM_API}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
        r.raise_for_status()
        return {"success": True, "message_id": r.json()["result"]["message_id"]}
    except Exception as e:
        return {"error": str(e)}


def send_signal(coin, price, change_24h, signal_type, reason,
                fear_greed=None, rsi=None, macd_trend=None) -> dict:
    """Kirim sinyal trading terformat ke Telegram — include RSI & MACD."""
    EMOJI = {"BUY": "🟢", "SELL": "🔴", "WATCH": "🟡", "HOLD": "⚪"}
    emoji = EMOJI.get(signal_type.upper(), "⚪")
    change_str = f"+{change_24h:.2f}%" if change_24h >= 0 else f"{change_24h:.2f}%"

    # Baris indikator teknikal
    indicators = []
    if rsi is not None:
        rsi_emoji = "🔥" if rsi >= 70 else "❄️" if rsi <= 30 else "➡️"
        indicators.append(f"RSI: {rsi} {rsi_emoji}")
    if macd_trend:
        macd_emoji = {"BULLISH": "📈", "BEARISH": "📉", "WEAKENING_BULL": "⚠️", "WEAKENING_BEAR": "⚠️"}.get(macd_trend, "➡️")
        indicators.append(f"MACD: {macd_trend} {macd_emoji}")
    if fear_greed is not None:
        indicators.append(f"Fear &amp; Greed: {fear_greed}/100")

    ind_str = " | ".join(indicators)
    ind_line = f"\n<code>{ind_str}</code>" if ind_str else ""

    text = f"""{emoji} <b>SINYAL {signal_type.upper()} — {coin.upper()}</b>

<b>Harga:</b> ${price:,.2f}  <b>24h:</b> {change_str}{ind_line}

<b>Analisis:</b>
{reason}

<i>— Crypto Intelligence Agent</i>"""

    return send_message(text)


def send_daily_report(market_data: dict, summary: str) -> dict:
    lines = ["<b>📊 Laporan Market Harian</b>\n"]
    for coin, data in market_data.items():
        change = data.get("change_24h_pct", 0)
        arrow = "▲" if change >= 0 else "▼"
        lines.append(f"<b>{coin.upper()}</b>: ${data['price_usd']:,.0f} ({arrow}{abs(change):.1f}%)")
    lines.append(f"\n{summary}\n<i>— Crypto Intelligence Agent</i>")
    return send_message("\n".join(lines))


def test_connection() -> bool:
    result = send_message("✅ <b>Crypto Agent aktif!</b>\nKoneksi Telegram berhasil.")
    return "success" in result
