"""
whale_tracker.py — Pantau transaksi whale crypto.

Sumber data (semua gratis):
  - Whale Alert API (free tier: 10 req/menit, data 1 jam terakhir)
  - Blockchair API (gratis, no key untuk BTC/ETH)

Setup Whale Alert (opsional tapi recommended):
  1. Daftar di https://whale-alert.io/
  2. Ambil API key gratis
  3. Tambah WHALE_ALERT_API_KEY di .env

Tanpa API key: pakai Blockchair sebagai fallback (BTC & ETH only)
"""

import requests
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

WHALE_ALERT_API = "https://api.whale-alert.io/v1"
BLOCKCHAIR_API = "https://api.blockchair.com"
HEADERS = {"User-Agent": "CryptoAgent/1.0"}

# Minimum transaksi yang dianggap "whale" dalam USD
MIN_WHALE_USD = 1_000_000  # $1 juta


def get_whale_transactions(min_usd: int = MIN_WHALE_USD, limit: int = 10) -> dict:
    """
    Ambil transaksi whale terbaru.
    Coba Whale Alert dulu, fallback ke Blockchair kalau tidak ada key.
    """
    api_key = os.environ.get("WHALE_ALERT_API_KEY", "")

    if api_key and api_key != "your_key_here":
        return _fetch_whale_alert(api_key, min_usd, limit)
    else:
        return _fetch_blockchair(min_usd, limit)


def _fetch_whale_alert(api_key: str, min_usd: int, limit: int) -> dict:
    """Fetch dari Whale Alert API."""
    try:
        r = requests.get(
            f"{WHALE_ALERT_API}/transactions",
            params={
                "api_key": api_key,
                "min_value": min_usd,
                "limit": limit,
                "cursor": 0,
            },
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        txs = []
        for tx in data.get("transactions", []):
            txs.append({
                "blockchain": tx.get("blockchain", "").upper(),
                "symbol": tx.get("symbol", "").upper(),
                "amount": tx.get("amount", 0),
                "amount_usd": tx.get("amount_usd", 0),
                "from": _label(tx.get("from", {})),
                "to": _label(tx.get("to", {})),
                "hash": tx.get("hash", "")[:16] + "...",
                "timestamp": datetime.fromtimestamp(
                    tx.get("timestamp", 0), tz=timezone.utc
                ).strftime("%H:%M UTC"),
            })

        return {
            "source": "Whale Alert",
            "transactions": txs,
            "count": len(txs),
            "min_usd": min_usd,
        }
    except Exception as e:
        return {"error": f"Whale Alert: {str(e)}"}


def _fetch_blockchair(min_usd: int, limit: int) -> dict:
    """
    Fallback: ambil transaksi besar BTC dari Blockchair (gratis, no key).
    """
    try:
        r = requests.get(
            f"{BLOCKCHAIR_API}/bitcoin/transactions",
            params={
                "s": "output_total_usd(desc)",
                "limit": limit,
                "q": f"output_total_usd({min_usd}..)",
            },
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        txs = []
        for tx in data.get("data", []):
            usd = tx.get("output_total_usd", 0)
            btc = tx.get("output_total", 0) / 1e8
            txs.append({
                "blockchain": "BITCOIN",
                "symbol": "BTC",
                "amount": round(btc, 4),
                "amount_usd": int(usd),
                "from": "Unknown",
                "to": "Unknown",
                "hash": tx.get("hash", "")[:16] + "...",
                "timestamp": tx.get("time", "")[:16],
            })

        return {
            "source": "Blockchair (BTC only — daftar Whale Alert untuk semua koin)",
            "transactions": txs,
            "count": len(txs),
            "min_usd": min_usd,
        }
    except Exception as e:
        return {"error": f"Blockchair: {str(e)}"}


def _label(entity: dict) -> str:
    """Format label dari/ke transaksi."""
    if not entity:
        return "Unknown"
    owner = entity.get("owner", "")
    owner_type = entity.get("owner_type", "")
    if owner:
        return f"{owner} ({owner_type})" if owner_type else owner
    return owner_type or "Unknown Wallet"


def format_whale_summary(data: dict) -> str:
    """Format data whale jadi teks yang bagus untuk Telegram/terminal."""
    if "error" in data:
        return f"Gagal ambil data whale: {data['error']}"

    txs = data.get("transactions", [])
    if not txs:
        return "Tidak ada transaksi whale besar saat ini."

    lines = [f"🐋 <b>Whale Transactions</b> (min ${data['min_usd']:,})\n"]
    for tx in txs[:5]:  # tampilkan max 5
        usd = tx['amount_usd']
        usd_str = f"${usd/1e6:.1f}M" if usd >= 1e6 else f"${usd:,}"
        lines.append(
            f"• <b>{tx['symbol']}</b> {tx['amount']:,.0f} ({usd_str})\n"
            f"  {tx['from']} → {tx['to']}\n"
            f"  {tx['timestamp']}"
        )

    lines.append(f"\n<i>Source: {data['source']}</i>")
    return "\n\n".join(lines)


def check_whale_activity(threshold_usd: int = MIN_WHALE_USD) -> dict:
    """
    Cek aktivitas whale dan return summary.
    Dipanggil oleh scheduler dan telegram_agent.
    """
    data = get_whale_transactions(min_usd=threshold_usd, limit=10)
    summary = format_whale_summary(data)
    return {
        "raw": data,
        "summary": summary,
        "has_activity": data.get("count", 0) > 0,
    }
