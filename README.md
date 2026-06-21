# Crypto Intelligence Agent

AI-powered crypto trading assistant with real-time analysis, multi-agent risk management, and automated Telegram alerts — built from scratch using free-tier APIs only.

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama%203.3-orange.svg)](https://groq.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

This is a conversational AI agent for crypto markets that combines large language model reasoning with quantitative technical analysis. It answers natural-language questions, generates scalping signals with concrete entry/exit levels, tracks whale wallet activity on-chain, and validates every trade idea through an automated risk-management layer before surfacing it to the user.

Talk to it on Telegram like you would a human analyst — "what's happening with ETH right now" or "give me a scalp setup on SOL" — and it fetches live data, runs the numbers, and replies in plain language.

## Why it's interesting

Most crypto bots are either pure LLM wrappers (no real data, prone to hallucinating prices) or pure rule-based scripts (no natural language understanding). This project combines both: an LLM orchestration layer for conversation and reasoning, backed by a deterministic multi-agent pipeline for anything involving real money decisions.

The multi-agent architecture (`DataAgent → AnalysisAgent → RiskAgent → Orchestrator`) means the system can explain *why* it rejected a technically-valid signal — for example, confidence too low, risk/reward unfavorable, or stop-loss placed too far from entry. That separation of concerns makes each component independently testable.

## Architecture

```
                    ┌─────────────────────┐
                    │   Telegram / CLI     │   ← user interface
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   LLM Agent (Groq)    │   ← conversational layer
                    │   11 callable tools   │      11 function-calling tools
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                       │
┌───────▼────────┐   ┌─────────▼─────────┐   ┌────────▼────────┐
│  Signal Engine  │   │  Multi-Agent       │   │  Monitoring      │
│  RSI/MACD/BB/   │   │  Pipeline          │   │  Scheduler +      │
│  EMA/Volume     │   │  Data→Analysis→Risk│   │  Whale Tracker   │
└───────┬────────┘   └─────────┬─────────┘   └────────┬────────┘
        │                      │                       │
        └──────────────────────┴──────────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Free public APIs    │
                    │   CoinGecko, Etherscan,│
                    │   BscScan, Alt.me      │
                    └───────────────────────┘
```

## Features

**Conversational AI** — Ask anything about crypto in natural language (Indonesian or English). Powered by Llama 3.3 70B via Groq's free tier, with 11 function-calling tools for live price, market overview, DeFi stats, news, gas fees, and coin search.

**Scalping signal engine** — Generates LONG/SHORT/WAIT signals with concrete entry, take-profit (TP1/TP2), and stop-loss levels. Entry and exit points are anchored to real support/resistance levels detected from swing-high/swing-low clustering, not arbitrary ATR multiples. Signals require confluence across 1H/4H/1D timeframes before triggering.

**Multi-agent risk management** — A dedicated `RiskAgent` validates every signal against configurable rules (minimum confidence, minimum risk/reward ratio, maximum stop-loss distance) before it reaches the user. Rejected signals come with a stated reason.

**Backtesting** — Replays the scalping strategy against historical OHLC data, simulating whether take-profit or stop-loss would have triggered first. Reports win rate, profit factor, and max drawdown.

**Whale tracking** — Monitors Ethereum and BSC for large native-coin transfers, labels known exchange wallets, and classifies flow direction (deposits to exchanges = bearish signal, withdrawals = bullish signal).

**Telegram integration** — Full bot with slash commands (`/scalp`, `/whale`, `/addalert`, `/market`) plus free-text conversation, price alerts with persistent state, and automated hourly market scans.

**Live ticker** — Terminal-based real-time price display with directional tick indicators.

## Tech stack

| Layer | Technology |
|---|---|
| LLM / reasoning | Groq API (Llama 3.3 70B), function calling |
| Technical analysis | pandas, `ta` (RSI, MACD, Bollinger Bands, EMA, ATR) |
| Data sources | CoinGecko, Alternative.me (Fear & Greed), Etherscan, BscScan, DeFiLlama |
| Messaging | Telegram Bot API (long polling) |
| Deployment | Railway / Render (Procfile-based worker) |

## Project structure

```
crypto_agent/
├── agent.py                 # LLM orchestration + 11-tool definitions
├── tools.py                 # Tool implementations (CoinGecko, news, DeFi, gas)
├── telegram_agent.py        # Interactive Telegram bot
├── scheduler.py             # Hourly automated market scanner
├── main.py                  # Cloud deployment entry point (runs both)
│
├── scalping_engine.py       # Core signal logic
├── support_resistance.py    # Swing-point detection & level clustering
├── multi_timeframe.py       # 1H/4H/1D confluence analysis
├── indicators.py            # Standalone RSI/MACD calculation
├── signal_engine.py         # Simpler price-action signal (v1)
│
├── agents/                  # Multi-agent pipeline
│   ├── data_agent.py        # Data collection only
│   ├── analysis_agent.py    # Signal generation only
│   ├── risk_agent.py        # Validation & position sizing only
│   └── orchestrator.py      # Coordinates the above
│
├── backtest_engine.py       # Historical strategy simulation
├── run_backtest.py          # Backtest CLI
├── run_agents.py            # Multi-agent pipeline CLI
│
├── whale_tracker.py         # Whale Alert / Blockchair (v1)
├── whale_tracker_v2.py      # ETH + BSC native tracker with exchange flow
├── price_alert.py           # Persistent price-target alerts
├── telegram_bot.py          # Telegram message formatting/sending
└── live_ticker.py           # Terminal live price display
```

## Setup

```bash
git clone https://github.com/yourusername/crypto-agent.git
cd crypto-agent
pip install -r requirements.txt
```

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_key          # free at console.groq.com
TELEGRAM_BOT_TOKEN=your_bot_token   # via @BotFather
TELEGRAM_CHAT_ID=your_chat_id
ETHERSCAN_API_KEY=optional          # free at etherscan.io/apis
BSCSCAN_API_KEY=optional            # free at bscscan.com/apis
```

```bash
# Verify free APIs work without any keys
python test_tools.py

# Run the conversational agent locally
python agent.py

# Run the interactive Telegram bot
python telegram_agent.py

# Generate a scalping signal
python scalping_bot.py --coin btc

# Run the multi-agent risk-validated pipeline
python run_agents.py --coin btc

# Backtest the strategy
python run_backtest.py --coin btc --days 30
```

## Deployment

This project deploys as a single worker process (`main.py`) that runs the Telegram bot and scheduler concurrently — designed for free-tier platforms that allocate one process per service.

**Railway:**
```bash
railway login
railway init
railway up
# set environment variables in the Railway dashboard
```

**Render:** connect the GitHub repo, set the start command to `python main.py`, add environment variables, and select the free worker plan.

## Sample backtest output

```
Backtest BITCOIN (30 days, 4H candles)
=============================================
Total trades    : 7
Win rate        : 42.9% (3W / 4L)
Avg win         : +2.68%
Avg loss        : -1.72%
Profit factor   : 1.17
Total return    : +1.15%
Max drawdown    : -6.90%
```

This is an early result on a small sample — the strategy is profitable but not yet robust. Backtesting is run continuously as more data accumulates; parameters are tuned against larger sample sizes rather than overfit to a single 30-day window.

## Disclaimer

This project is for educational purposes and does not constitute financial advice. Signals are generated from public technical indicators and historical patterns, which are not guarantees of future performance. The system does not execute trades automatically — all signals are informational and require manual execution with the user's own risk management.

## License

MIT
