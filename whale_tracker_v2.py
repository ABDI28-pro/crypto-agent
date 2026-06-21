"""
whale_tracker_v2.py — Super Whale Tracker untuk Ethereum + BSC.

Sumber data (semua gratis, no key wajib):
  - Etherscan API   → transaksi besar di Ethereum
  - BscScan API     → transaksi besar di BSC
  - Whale Alert API → fallback multi-chain (opsional, perlu key gratis)

Mendeteksi:
  1. Whale deposit/withdraw dari/ke exchange wallet dikenal
  2. Wallet besar (non-exchange) yang baru transaksi token signifikan
  3. Native coin (ETH/BNB) transfer besar

Setup opsional untuk hasil lebih lengkap:
  ETHERSCAN_API_KEY  — daftar gratis di etherscan.io/apis
  BSCSCAN_API_KEY    — daftar gratis di bscscan.com/apis
  (tanpa key: pakai rate limit publik yang lebih ketat tapi tetap jalan)
"""

import requests
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

ETHERSCAN_API = "https://api.etherscan.io/api"
BSCSCAN_API = "https://api.bscscan.com/api"
HEADERS = {"User-Agent": "CryptoAgent/1.0"}

ETHERSCAN_KEY = os.environ.get("ETHERSCAN_API_KEY", "YourApiKeyToken")
BSCSCAN_KEY = os.environ.get("BSCSCAN_API_KEY", "YourApiKeyToken")

# Label wallet exchange terkenal (untuk deteksi deposit/withdraw)
KNOWN_EXCHANGE_WALLETS = {
    # Ethereum
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance 14",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance 15",
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": "Binance 16",
    "0x5a52e96bacdabb82fd05763e25335261b270efcb": "Binance 7",
    "0x0d0707963952f2fba59dd06f2b425ace40b492fe": "Gate.io",
    "0x46340b20830761efd32832a74d7169b29feb9758": "Crypto.com",
    "0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2": "Binance Hot Wallet",
    # BSC
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3": "Binance Hot Wallet (BSC)",
    "0xf977814e90da44bfa03b6295a0616a897441acec": "Binance Cold Wallet",
}

# Token kontrak utama yang dipantau (Ethereum)
ETH_MAJOR_TOKENS = {
    "0xdAC17F958D2ee523a2206206994597C13D831ec7": "USDT",
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48": "USDC",
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599": "WBTC",
    "0x514910771AF9Ca656af840dff83E8264EcF986CA": "LINK",
    "0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0": "MATIC",
}

MIN_USD_DEFAULT = 500_000  # threshold "whale" dalam USD


def get_eth_large_transfers(min_eth: float = 100) -> dict:
    """
    Ambil transaksi ETH besar terbaru dari Etherscan.
    min_eth: minimum jumlah ETH dianggap whale (default 100 ETH).
    """
    try:
        # Ambil blok terbaru
        r = requests.get(ETHERSCAN_API, params={
            "module": "proxy", "action": "eth_blockNumber",
            "apikey": ETHERSCAN_KEY,
        }, headers=HEADERS, timeout=10)
        latest_block = int(r.json()["result"], 16)

        # Ambil transaksi dari beberapa blok terakhir
        txs_found = []
        for block_offset in range(0, 3):
            block_num = latest_block - block_offset
            r2 = requests.get(ETHERSCAN_API, params={
                "module": "proxy", "action": "eth_getBlockByNumber",
                "tag": hex(block_num), "boolean": "true",
                "apikey": ETHERSCAN_KEY,
            }, headers=HEADERS, timeout=10)
            block_data = r2.json().get("result", {})
            transactions = block_data.get("transactions", [])

            for tx in transactions:
                value_wei = int(tx.get("value", "0x0"), 16)
                value_eth = value_wei / 1e18
                if value_eth >= min_eth:
                    txs_found.append({
                        "chain": "Ethereum",
                        "symbol": "ETH",
                        "amount": round(value_eth, 2),
                        "from": _label_wallet(tx.get("from", "")),
                        "to": _label_wallet(tx.get("to", "")),
                        "hash": tx.get("hash", "")[:18] + "...",
                        "block": block_num,
                    })

        return {"transactions": txs_found, "chain": "Ethereum", "min_eth": min_eth}
    except Exception as e:
        return {"error": f"Ethereum: {str(e)}"}


def get_bsc_large_transfers(min_bnb: float = 500) -> dict:
    """
    Ambil transaksi BNB besar terbaru dari BscScan.
    min_bnb: minimum jumlah BNB dianggap whale (default 500 BNB).
    """
    try:
        r = requests.get(BSCSCAN_API, params={
            "module": "proxy", "action": "eth_blockNumber",
            "apikey": BSCSCAN_KEY,
        }, headers=HEADERS, timeout=10)
        latest_block = int(r.json()["result"], 16)

        txs_found = []
        for block_offset in range(0, 3):
            block_num = latest_block - block_offset
            r2 = requests.get(BSCSCAN_API, params={
                "module": "proxy", "action": "eth_getBlockByNumber",
                "tag": hex(block_num), "boolean": "true",
                "apikey": BSCSCAN_KEY,
            }, headers=HEADERS, timeout=10)
            block_data = r2.json().get("result", {})
            transactions = block_data.get("transactions", [])

            for tx in transactions:
                value_wei = int(tx.get("value", "0x0"), 16)
                value_bnb = value_wei / 1e18
                if value_bnb >= min_bnb:
                    txs_found.append({
                        "chain": "BSC",
                        "symbol": "BNB",
                        "amount": round(value_bnb, 2),
                        "from": _label_wallet(tx.get("from", "")),
                        "to": _label_wallet(tx.get("to", "")),
                        "hash": tx.get("hash", "")[:18] + "...",
                        "block": block_num,
                    })

        return {"transactions": txs_found, "chain": "BSC", "min_bnb": min_bnb}
    except Exception as e:
        return {"error": f"BSC: {str(e)}"}


def get_token_whale_moves(token_address: str, chain: str = "ethereum", min_value_usd: float = MIN_USD_DEFAULT) -> dict:
    """
    Ambil transfer token (ERC20/BEP20) besar untuk kontrak tertentu.
    """
    api_url = ETHERSCAN_API if chain == "ethereum" else BSCSCAN_API
    api_key = ETHERSCAN_KEY if chain == "ethereum" else BSCSCAN_KEY

    try:
        r = requests.get(api_url, params={
            "module": "account", "action": "tokentx",
            "contractaddress": token_address,
            "page": 1, "offset": 30, "sort": "desc",
            "apikey": api_key,
        }, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "1":
            return {"error": data.get("message", "No data"), "transactions": []}

        txs = []
        for tx in data.get("result", [])[:15]:
            decimals = int(tx.get("tokenDecimal", 18))
            amount = int(tx.get("value", "0")) / (10 ** decimals)
            txs.append({
                "chain": chain.upper(),
                "symbol": tx.get("tokenSymbol", "?"),
                "amount": round(amount, 2),
                "from": _label_wallet(tx.get("from", "")),
                "to": _label_wallet(tx.get("to", "")),
                "hash": tx.get("hash", "")[:18] + "...",
                "timestamp": datetime.fromtimestamp(
                    int(tx.get("timeStamp", 0)), tz=timezone.utc
                ).strftime("%H:%M UTC"),
            })

        return {"transactions": txs, "chain": chain}
    except Exception as e:
        return {"error": str(e)}


def detect_exchange_flow(transactions: list) -> dict:
    """
    Analisis arah dana: masuk ke exchange (whale mau jual/withdraw profit)
    atau keluar dari exchange (whale mau hodl/akumulasi).
    """
    inflow_to_exchange = []   # whale → exchange (bearish signal, mau jual)
    outflow_from_exchange = []  # exchange → whale (bullish signal, mau hodl)
    wallet_to_wallet = []

    for tx in transactions:
        from_is_exchange = any(name in tx["from"] for name in ["Binance", "Gate.io", "Crypto.com"])
        to_is_exchange = any(name in tx["to"] for name in ["Binance", "Gate.io", "Crypto.com"])

        if to_is_exchange and not from_is_exchange:
            inflow_to_exchange.append(tx)
        elif from_is_exchange and not to_is_exchange:
            outflow_from_exchange.append(tx)
        else:
            wallet_to_wallet.append(tx)

    return {
        "inflow_to_exchange": inflow_to_exchange,
        "outflow_from_exchange": outflow_from_exchange,
        "wallet_to_wallet": wallet_to_wallet,
        "signal": _interpret_flow(len(inflow_to_exchange), len(outflow_from_exchange)),
    }


def _interpret_flow(inflow_count: int, outflow_count: int) -> str:
    if inflow_count > outflow_count * 1.5:
        return "BEARISH — Lebih banyak whale kirim ke exchange (potensi jual)"
    elif outflow_count > inflow_count * 1.5:
        return "BULLISH — Lebih banyak whale tarik dari exchange (potensi hodl/akumulasi)"
    else:
        return "NEUTRAL — Arus masuk/keluar exchange seimbang"


def _label_wallet(address: str) -> str:
    """Beri label kalau wallet dikenal, kalau tidak tampilkan address singkat."""
    if not address:
        return "Unknown"
    addr_lower = address.lower()
    for known_addr, label in KNOWN_EXCHANGE_WALLETS.items():
        if known_addr.lower() == addr_lower:
            return f"{label} 🏦"
    return f"{address[:8]}...{address[-6:]}"


def scan_whale_activity(chains: list = None, min_usd: float = MIN_USD_DEFAULT) -> dict:
    """
    Scan utama — gabungkan ETH + BSC whale activity jadi satu laporan.
    """
    if chains is None:
        chains = ["ethereum", "bsc"]

    all_txs = []
    errors = []

    if "ethereum" in chains:
        eth_result = get_eth_large_transfers(min_eth=100)
        if "error" in eth_result:
            errors.append(eth_result["error"])
        else:
            all_txs += eth_result.get("transactions", [])

    if "bsc" in chains:
        bsc_result = get_bsc_large_transfers(min_bnb=500)
        if "error" in bsc_result:
            errors.append(bsc_result["error"])
        else:
            all_txs += bsc_result.get("transactions", [])

    flow_analysis = detect_exchange_flow(all_txs)

    return {
        "transactions": all_txs,
        "count": len(all_txs),
        "flow_analysis": flow_analysis,
        "errors": errors,
    }


def format_whale_report(data: dict) -> str:
    """Format hasil scan jadi teks rapi untuk Telegram/terminal."""
    txs = data.get("transactions", [])
    flow = data.get("flow_analysis", {})

    if not txs:
        msg = "🐋 <b>Whale Activity</b>\n\nTidak ada transaksi whale besar dalam beberapa blok terakhir."
        if data.get("errors"):
            msg += f"\n\n⚠️ {'; '.join(data['errors'][:2])}"
        return msg

    lines = [f"🐋 <b>Whale Activity Report</b> ({len(txs)} transaksi)\n"]
    lines.append(f"<b>Signal:</b> {flow.get('signal', 'N/A')}\n")

    for tx in txs[:8]:
        lines.append(
            f"• <b>{tx['amount']:,.2f} {tx['symbol']}</b> [{tx['chain']}]\n"
            f"  {tx['from']} → {tx['to']}"
        )

    inflow = len(flow.get("inflow_to_exchange", []))
    outflow = len(flow.get("outflow_from_exchange", []))
    lines.append(f"\n📥 Masuk exchange: {inflow} tx | 📤 Keluar exchange: {outflow} tx")

    return "\n".join(lines)
