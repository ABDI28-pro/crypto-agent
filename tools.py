"""
tools.py — Super Crypto Agent Tools
Semua API gratis, no key required (kecuali Whale Alert opsional)
"""

import requests

COINGECKO = "https://api.coingecko.com/api/v3"
HEADERS = {"User-Agent": "CryptoAgent/1.0"}

COIN_IDS = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "sol": "solana", "solana": "solana",
    "bnb": "binancecoin", "binancecoin": "binancecoin",
    "xrp": "ripple", "ripple": "ripple",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "ada": "cardano", "cardano": "cardano",
    "avax": "avalanche-2", "avalanche": "avalanche-2",
    "dot": "polkadot", "polkadot": "polkadot",
    "link": "chainlink", "chainlink": "chainlink",
    "matic": "matic-network", "polygon": "matic-network",
    "uni": "uniswap", "uniswap": "uniswap",
    "atom": "cosmos", "cosmos": "cosmos",
    "ltc": "litecoin", "litecoin": "litecoin",
    "etc": "ethereum-classic",
    "xlm": "stellar", "stellar": "stellar",
    "algo": "algorand", "algorand": "algorand",
    "near": "near", "icp": "internet-computer",
    "apt": "aptos", "aptos": "aptos",
    "arb": "arbitrum", "arbitrum": "arbitrum",
    "op": "optimism", "optimism": "optimism",
    "sui": "sui", "inj": "injective-protocol",
    "sei": "sei-network", "tia": "celestia",
}


def get_crypto_price(coin: str) -> dict:
    """Ambil harga real-time, change 24h, market cap, volume satu koin."""
    coin_id = COIN_IDS.get(coin.lower(), coin.lower())
    try:
        r = requests.get(
            f"{COINGECKO}/simple/price",
            params={"ids": coin_id, "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true"},
            headers=HEADERS, timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if coin_id not in data:
            return {"error": f"Koin '{coin}' tidak ditemukan."}
        d = data[coin_id]
        return {
            "coin": coin_id, "symbol": coin.upper(),
            "price_usd": d["usd"],
            "change_24h_pct": round(d.get("usd_24h_change", 0), 2),
            "market_cap_usd": int(d.get("usd_market_cap", 0)),
            "volume_24h_usd": int(d.get("usd_24h_vol", 0)),
        }
    except Exception as e:
        return {"error": str(e)}


def get_market_overview(coins: list = None) -> dict:
    """Ambil overview beberapa koin sekaligus."""
    if not coins:
        coins = ["bitcoin", "ethereum", "solana", "binancecoin", "ripple"]
    try:
        r = requests.get(
            f"{COINGECKO}/simple/price",
            params={"ids": ",".join(coins), "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true"},
            headers=HEADERS, timeout=10,
        )
        r.raise_for_status()
        result = {}
        for coin_id, d in r.json().items():
            result[coin_id] = {
                "price_usd": d["usd"],
                "change_24h_pct": round(d.get("usd_24h_change", 0), 2),
                "market_cap_usd": int(d.get("usd_market_cap", 0)),
                "volume_24h_usd": int(d.get("usd_24h_vol", 0)),
            }
        return result
    except Exception as e:
        return {"error": str(e)}


def get_fear_and_greed() -> dict:
    """Ambil Fear & Greed Index hari ini + kemarin."""
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=3", timeout=10)
        r.raise_for_status()
        items = r.json()["data"]
        today = items[0]
        result = {
            "value": int(today["value"]),
            "label": today["value_classification"],
            "interpretation": _interpret_fng(int(today["value"])),
        }
        if len(items) > 1:
            result["yesterday_value"] = int(items[1]["value"])
            result["yesterday_label"] = items[1]["value_classification"]
        return result
    except Exception as e:
        return {"error": str(e)}


def get_trending_coins() -> dict:
    """Ambil 7 koin trending di CoinGecko hari ini."""
    try:
        r = requests.get(f"{COINGECKO}/search/trending", headers=HEADERS, timeout=10)
        r.raise_for_status()
        coins = []
        for item in r.json().get("coins", [])[:7]:
            c = item["item"]
            coins.append({
                "name": c["name"], "symbol": c["symbol"].upper(),
                "market_cap_rank": c.get("market_cap_rank", "?"),
            })
        return {"trending": coins, "count": len(coins)}
    except Exception as e:
        return {"error": str(e)}


def get_global_market_stats() -> dict:
    """Total market cap, dominasi BTC/ETH, jumlah koin aktif."""
    try:
        r = requests.get(f"{COINGECKO}/global", headers=HEADERS, timeout=10)
        r.raise_for_status()
        d = r.json()["data"]
        return {
            "total_market_cap_usd": int(d["total_market_cap"]["usd"]),
            "total_volume_24h_usd": int(d["total_volume"]["usd"]),
            "btc_dominance_pct": round(d["market_cap_percentage"]["btc"], 1),
            "eth_dominance_pct": round(d["market_cap_percentage"]["eth"], 1),
            "active_coins": d["active_cryptocurrencies"],
            "market_cap_change_24h_pct": round(d["market_cap_change_percentage_24h_usd"], 2),
        }
    except Exception as e:
        return {"error": str(e)}


def get_top_coins_by_market_cap(limit: int = 20) -> dict:
    """Ambil top N koin by market cap dengan data lengkap."""
    try:
        r = requests.get(
            f"{COINGECKO}/coins/markets",
            params={"vs_currency": "usd", "order": "market_cap_desc",
                    "per_page": min(limit, 100), "page": 1,
                    "price_change_percentage": "24h,7d"},
            headers=HEADERS, timeout=15,
        )
        r.raise_for_status()
        coins = []
        for c in r.json():
            coins.append({
                "rank": c["market_cap_rank"],
                "name": c["name"],
                "symbol": c["symbol"].upper(),
                "price_usd": c["current_price"],
                "change_24h_pct": round(c.get("price_change_percentage_24h") or 0, 2),
                "change_7d_pct": round(c.get("price_change_percentage_7d_in_currency") or 0, 2),
                "market_cap_usd": c.get("market_cap") or 0,
                "volume_24h_usd": c.get("total_volume") or 0,
            })
        return {"coins": coins, "count": len(coins)}
    except Exception as e:
        return {"error": str(e)}


def get_coin_detail(coin: str) -> dict:
    """
    Ambil detail lengkap sebuah koin: deskripsi, ATH, ATL,
    supply, links, kategori, developer activity.
    """
    coin_id = COIN_IDS.get(coin.lower(), coin.lower())
    try:
        r = requests.get(
            f"{COINGECKO}/coins/{coin_id}",
            params={"localization": "false", "tickers": "false",
                    "market_data": "true", "community_data": "false",
                    "developer_data": "false"},
            headers=HEADERS, timeout=15,
        )
        r.raise_for_status()
        d = r.json()
        md = d.get("market_data", {})
        return {
            "name": d["name"],
            "symbol": d["symbol"].upper(),
            "description": d.get("description", {}).get("en", "")[:500],
            "categories": d.get("categories", [])[:5],
            "website": d.get("links", {}).get("homepage", [""])[0],
            "price_usd": md.get("current_price", {}).get("usd", 0),
            "ath_usd": md.get("ath", {}).get("usd", 0),
            "ath_change_pct": round(md.get("ath_change_percentage", {}).get("usd", 0), 2),
            "atl_usd": md.get("atl", {}).get("usd", 0),
            "circulating_supply": md.get("circulating_supply", 0),
            "max_supply": md.get("max_supply", 0),
            "market_cap_rank": d.get("market_cap_rank", 0),
            "sentiment_votes_up_pct": d.get("sentiment_votes_up_percentage", 0),
        }
    except Exception as e:
        return {"error": str(e)}


def get_crypto_news() -> dict:
    """
    Ambil berita crypto terbaru dari CoinGecko news feed.
    """
    try:
        r = requests.get(
            f"{COINGECKO}/news",
            headers=HEADERS, timeout=10,
        )
        r.raise_for_status()
        articles = []
        for item in r.json().get("data", [])[:8]:
            articles.append({
                "title": item.get("title", ""),
                "description": item.get("description", "")[:200],
                "author": item.get("author", ""),
                "published_at": item.get("published_at", ""),
                "url": item.get("url", ""),
            })
        return {"articles": articles, "count": len(articles)}
    except Exception as e:
        return {"error": str(e)}


def get_defi_stats() -> dict:
    """
    Ambil statistik DeFi global: total TVL, top protocols.
    Sumber: DeFiLlama (gratis, no key).
    """
    try:
        r = requests.get("https://api.llama.fi/v2/chains", timeout=10)
        r.raise_for_status()
        chains = r.json()[:10]

        r2 = requests.get("https://api.llama.fi/v2/protocols", timeout=10)
        r2.raise_for_status()
        protocols = sorted(r2.json(), key=lambda x: x.get("tvl", 0), reverse=True)[:10]

        top_chains = [{"name": c["name"], "tvl_usd": int(c.get("tvl", 0))} for c in chains]
        top_protocols = [{"name": p["name"], "chain": p.get("chain", ""), "tvl_usd": int(p.get("tvl", 0))} for p in protocols]

        total_tvl = sum(c.get("tvl", 0) for c in chains)
        return {
            "total_tvl_usd": int(total_tvl),
            "top_chains": top_chains[:5],
            "top_protocols": top_protocols[:5],
        }
    except Exception as e:
        return {"error": str(e)}


def get_eth_gas() -> dict:
    """
    Ambil harga gas Ethereum sekarang (gwei).
    Sumber: Etherscan public API (no key untuk basic).
    """
    try:
        r = requests.get(
            "https://api.etherscan.io/api",
            params={"module": "gastracker", "action": "gasoracle"},
            timeout=10,
        )
        r.raise_for_status()
        result = r.json().get("result", {})
        return {
            "safe_gwei": result.get("SafeGasPrice", "?"),
            "propose_gwei": result.get("ProposeGasPrice", "?"),
            "fast_gwei": result.get("FastGasPrice", "?"),
            "note": "Safe=ekonomis, Propose=normal, Fast=cepat",
        }
    except Exception as e:
        return {"error": str(e)}


def search_coin(query: str) -> dict:
    """
    Cari koin berdasarkan nama atau simbol.
    Berguna kalau user tanya koin yang tidak ada di daftar.
    """
    try:
        r = requests.get(
            f"{COINGECKO}/search",
            params={"query": query},
            headers=HEADERS, timeout=10,
        )
        r.raise_for_status()
        results = []
        for c in r.json().get("coins", [])[:5]:
            results.append({
                "id": c["id"],
                "name": c["name"],
                "symbol": c["symbol"].upper(),
                "market_cap_rank": c.get("market_cap_rank", "?"),
            })
        return {"results": results, "query": query}
    except Exception as e:
        return {"error": str(e)}


def _interpret_fng(value: int) -> str:
    if value <= 25: return "Pasar sangat takut. Historis bagus untuk akumulasi."
    elif value <= 45: return "Pasar takut. Sentimen negatif, bisa jadi opportunity."
    elif value <= 55: return "Sentimen netral. Market belum punya arah jelas."
    elif value <= 75: return "Pasar serakah. Banyak FOMO, hati-hati."
    else: return "Pasar sangat serakah. Risiko tinggi, potensi koreksi."


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_crypto_price",
            "description": "Ambil harga real-time, change 24h, market cap, volume satu koin. Pakai untuk pertanyaan harga spesifik.",
            "parameters": {
                "type": "object",
                "properties": {"coin": {"type": "string", "description": "Nama atau simbol koin, misal: bitcoin, ETH, SOL"}},
                "required": ["coin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_overview",
            "description": "Ambil snapshot beberapa koin sekaligus. Pakai untuk pertanyaan umum kondisi market atau perbandingan koin.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coins": {"type": "array", "items": {"type": "string"}, "description": "List coin ID CoinGecko"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fear_and_greed",
            "description": "Ambil Fear & Greed Index crypto hari ini. 0=extreme fear, 100=extreme greed.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trending_coins",
            "description": "Ambil 7 koin yang paling banyak dicari di CoinGecko hari ini.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_global_market_stats",
            "description": "Ambil statistik global: total market cap, dominasi BTC/ETH, volume 24h, jumlah koin aktif.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_coins_by_market_cap",
            "description": "Ambil top N koin by market cap dengan harga, change 24h dan 7d. Pakai untuk pertanyaan ranking atau koin terbesar.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "description": "Jumlah koin (default 20, max 100)"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_coin_detail",
            "description": "Ambil detail lengkap koin: deskripsi, ATH, ATL, supply, sentiment. Pakai untuk pertanyaan mendalam tentang satu koin.",
            "parameters": {
                "type": "object",
                "properties": {"coin": {"type": "string", "description": "Nama atau simbol koin"}},
                "required": ["coin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_news",
            "description": "Ambil berita crypto terbaru. Pakai untuk pertanyaan tentang news, kejadian terkini, atau sentimen berita.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_defi_stats",
            "description": "Ambil statistik DeFi global: total TVL, top chains, top protocols. Pakai untuk pertanyaan tentang DeFi.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_eth_gas",
            "description": "Ambil harga gas Ethereum sekarang dalam gwei. Pakai untuk pertanyaan tentang biaya transaksi ETH.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_coin",
            "description": "Cari koin berdasarkan nama atau simbol. Pakai kalau koin tidak dikenali atau user tanya koin yang tidak umum.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Nama atau simbol koin yang dicari"}},
                "required": ["query"],
            },
        },
    },
]

TOOL_MAP = {
    "get_crypto_price": get_crypto_price,
    "get_market_overview": get_market_overview,
    "get_fear_and_greed": get_fear_and_greed,
    "get_trending_coins": get_trending_coins,
    "get_global_market_stats": get_global_market_stats,
    "get_top_coins_by_market_cap": get_top_coins_by_market_cap,
    "get_coin_detail": get_coin_detail,
    "get_crypto_news": get_crypto_news,
    "get_defi_stats": get_defi_stats,
    "get_eth_gas": get_eth_gas,
    "search_coin": search_coin,
}
