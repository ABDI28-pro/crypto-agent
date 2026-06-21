"""
agent.py — Super Crypto Agent pakai Groq (gratis).
11 tools: harga, market, news, DeFi, gas, whale, search, dan lain-lain.
"""

import json
import os
from dotenv import load_dotenv
from groq import Groq
from tools import TOOL_DEFINITIONS, TOOL_MAP

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
MAX_LOOP = 10

SYSTEM_PROMPT = """Kamu adalah Super Crypto Intelligence Agent — analis crypto paling lengkap dan cerdas.

Kemampuanmu (11 tools):
- Harga real-time koin apa saja (get_crypto_price)
- Overview beberapa koin sekaligus (get_market_overview)
- Fear & Greed Index (get_fear_and_greed)
- Koin trending hari ini (get_trending_coins)
- Statistik global market (get_global_market_stats)
- Top 100 koin by market cap (get_top_coins_by_market_cap)
- Detail lengkap koin: ATH, ATL, supply, sentiment (get_coin_detail)
- Berita crypto terbaru (get_crypto_news)
- Statistik DeFi: TVL, top protocols (get_defi_stats)
- Harga gas Ethereum (get_eth_gas)
- Cari koin yang tidak dikenal (search_coin)

Pengetahuan umum yang bisa kamu jelaskan tanpa tools:
- Cara kerja blockchain, Bitcoin, Ethereum, DeFi, NFT, Layer 2
- Strategi trading: DCA, swing trading, futures, options
- Teknikal analisis: RSI, MACD, Bollinger Bands, support/resistance
- Fundamental analisis: tokenomics, use case, tim, roadmap
- Risiko dan manajemen portfolio
- Terminologi crypto: HODL, FOMO, FUD, whale, rug pull, dll
- Regulasi crypto di berbagai negara
- Pajak crypto
- Cara pakai DEX, CEX, wallet, bridge

Aturan penting:
1. SELALU fetch data real-time sebelum sebut angka harga atau market data
2. Kalau butuh banyak data, panggil BEBERAPA tools sekaligus
3. Kalau koin tidak dikenal, gunakan search_coin dulu
4. Jawab dalam Bahasa Indonesia yang santai dan informatif
5. Berikan insight actionable, bukan hanya data mentah
6. Untuk pertanyaan edukasi/konsep, jawab langsung tanpa tools
7. Selalu tambahkan disclaimer bahwa ini bukan financial advice

Format jawaban:
- Ringkas dan padat untuk pertanyaan sederhana
- Lebih detail untuk analisis mendalam
- Gunakan bullet points untuk info yang banyak
- Selalu tutup dengan insight atau catatan penting
"""


def run_tool(name: str, arguments: dict) -> str:
    print(f"  → {name}({arguments})")
    fn = TOOL_MAP.get(name)
    if not fn:
        return json.dumps({"error": f"Tool '{name}' tidak ada."})
    try:
        return json.dumps(fn(**arguments), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def ask_agent(question: str, history: list = None) -> tuple[str, list]:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history or []
    messages.append({"role": "user", "content": question})

    for _ in range(MAX_LOOP):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=3000,
        )
        msg = response.choices[0].message
        finish = response.choices[0].finish_reason
        messages.append(msg)

        if finish == "stop" or not msg.tool_calls:
            history_out = [m for m in messages if not (isinstance(m, dict) and m.get("role") == "system")]
            return msg.content or "", history_out

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = run_tool(tc.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return "Maaf, tidak bisa menyelesaikan permintaan.", history or []


def chat():
    print("\n" + "=" * 56)
    print("  Super Crypto Intelligence Agent")
    print("  11 tools · Berita · DeFi · Gas · Whale · Search")
    print("  Tanya apa saja tentang crypto!")
    print("  Ketik 'exit' untuk keluar, 'reset' untuk mulai ulang")
    print("=" * 56 + "\n")

    history = []
    while True:
        try:
            user_input = input("Kamu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSampai jumpa!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "keluar"):
            print("Sampai jumpa!")
            break
        if user_input.lower() == "reset":
            history = []
            print("[History direset]\n")
            continue

        print()
        answer, history = ask_agent(user_input, history)
        print(f"Agent:\n{answer}\n")
        print("-" * 56 + "\n")


if __name__ == "__main__":
    chat()
