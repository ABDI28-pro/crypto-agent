"""
multi_timeframe.py — Analisis multi-timeframe untuk konfirmasi sinyal.

Prinsip: sinyal scalping yang valid harus didukung minimal 2 dari 3 timeframe.
  - 1H : momentum jangka pendek (entry timing)
  - 4H : trend menengah (konfirmasi arah)
  - 1D : trend besar (filter — jangan LONG kalau 1D downtrend kuat)

CoinGecko OHLC granularity otomatis berdasarkan parameter 'days':
  days=1   → candle ~30 menit (kita pakai sebagai proxy 1H)
  days=7   → candle ~4 jam   (proxy 4H)
  days=30  → candle ~4 jam (lebih banyak data, proxy 1D trend)
"""

import requests
import pandas as pd
import ta

COINGECKO = "https://api.coingecko.com/api/v3"
HEADERS = {"User-Agent": "CryptoAgent/1.0"}


def fetch_ohlc(coin_id: str, days: int) -> pd.DataFrame:
    """Fetch OHLC dari CoinGecko untuk timeframe tertentu."""
    try:
        r = requests.get(
            f"{COINGECKO}/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": days},
            headers=HEADERS, timeout=10,
        )
        r.raise_for_status()
        df = pd.DataFrame(r.json(), columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["volume"] = (df["high"] - df["low"]) * df["close"]
        return df.sort_values("timestamp").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def get_trend_bias(df: pd.DataFrame) -> dict:
    """
    Tentukan bias trend dari satu timeframe pakai EMA + RSI sederhana.
    Return: {"bias": "BULLISH"/"BEARISH"/"NEUTRAL", "rsi": float, "ema_aligned": bool}
    """
    if df.empty or len(df) < 25:
        return {"bias": "UNKNOWN", "rsi": None, "ema_aligned": False}

    close = df["close"]
    ema9 = ta.trend.EMAIndicator(close=close, window=9).ema_indicator().iloc[-1]
    ema21 = ta.trend.EMAIndicator(close=close, window=21).ema_indicator().iloc[-1]
    rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]
    price = close.iloc[-1]

    bullish_align = price > ema9 > ema21
    bearish_align = price < ema9 < ema21

    if bullish_align and rsi > 50:
        bias = "BULLISH"
    elif bearish_align and rsi < 50:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return {
        "bias": bias,
        "rsi": round(float(rsi), 1),
        "ema_aligned": bullish_align or bearish_align,
        "price": round(float(price), 6),
    }


def analyze_multi_timeframe(coin_id: str) -> dict:
    """
    Analisis 3 timeframe sekaligus, return konfirmasi & confluence score.

    Returns:
        {
            "1h": {...}, "4h": {...}, "1d": {...},
            "confluence": "BULLISH"/"BEARISH"/"MIXED",
            "confluence_score": 0-3,  (berapa TF yang searah)
            "warning": str atau None
        }
    """
    df_1h = fetch_ohlc(coin_id, days=1)    # candle pendek, proxy 1H
    df_4h = fetch_ohlc(coin_id, days=7)    # proxy 4H
    df_1d = fetch_ohlc(coin_id, days=30)   # proxy 1D trend besar

    tf_1h = get_trend_bias(df_1h)
    tf_4h = get_trend_bias(df_4h)
    tf_1d = get_trend_bias(df_1d)

    biases = [tf_1h["bias"], tf_4h["bias"], tf_1d["bias"]]
    bullish_count = biases.count("BULLISH")
    bearish_count = biases.count("BEARISH")

    if bullish_count >= 2:
        confluence = "BULLISH"
        confluence_score = bullish_count
    elif bearish_count >= 2:
        confluence = "BEARISH"
        confluence_score = bearish_count
    else:
        confluence = "MIXED"
        confluence_score = max(bullish_count, bearish_count)

    warning = None
    if tf_1d["bias"] == "BEARISH" and tf_1h["bias"] == "BULLISH":
        warning = "1H bullish tapi 1D masih downtrend — risiko counter-trend, kurangi size"
    elif tf_1d["bias"] == "BULLISH" and tf_1h["bias"] == "BEARISH":
        warning = "1H bearish tapi 1D masih uptrend — bisa jadi pullback sementara, bukan reversal"

    return {
        "1h": tf_1h,
        "4h": tf_4h,
        "1d": tf_1d,
        "confluence": confluence,
        "confluence_score": confluence_score,
        "warning": warning,
    }
