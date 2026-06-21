"""
indicators.py — Hitung RSI dan MACD dari data OHLCV.

Sumber data: CoinGecko public API (gratis, no key)
Library    : pandas + ta

Cara pakai:
    from indicators import get_indicators
    result = get_indicators("bitcoin")
    print(result)
"""

import requests
import pandas as pd
import ta

COINGECKO = "https://api.coingecko.com/api/v3"
HEADERS = {"User-Agent": "CryptoAgent/1.0"}


def fetch_ohlcv(coin_id: str, days: int = 30) -> pd.DataFrame:
    """
    Ambil data OHLCV dari CoinGecko.
    Return DataFrame dengan kolom: timestamp, open, high, low, close, volume
    """
    try:
        r = requests.get(
            f"{COINGECKO}/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": days},
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    except Exception as e:
        return pd.DataFrame()


def calc_rsi(df: pd.DataFrame, period: int = 14) -> float:
    """
    Hitung RSI (Relative Strength Index).
    - RSI > 70 = Overbought (harga kemungkinan turun)
    - RSI < 30 = Oversold (harga kemungkinan naik)
    - RSI 30-70 = Netral
    """
    if df.empty or len(df) < period + 1:
        return None
    rsi_series = ta.momentum.RSIIndicator(close=df["close"], window=period).rsi()
    return round(float(rsi_series.iloc[-1]), 2)


def calc_macd(df: pd.DataFrame) -> dict:
    """
    Hitung MACD (Moving Average Convergence Divergence).
    - MACD line > Signal line = Bullish (momentum naik)
    - MACD line < Signal line = Bearish (momentum turun)
    - Histogram positif & membesar = momentum makin kuat
    """
    if df.empty or len(df) < 26:
        return {}

    macd = ta.trend.MACD(close=df["close"])
    macd_line = round(float(macd.macd().iloc[-1]), 4)
    signal_line = round(float(macd.macd_signal().iloc[-1]), 4)
    histogram = round(float(macd.macd_diff().iloc[-1]), 4)

    # Tentukan arah
    if macd_line > signal_line and histogram > 0:
        trend = "BULLISH"
        desc = "MACD di atas signal, momentum naik"
    elif macd_line < signal_line and histogram < 0:
        trend = "BEARISH"
        desc = "MACD di bawah signal, momentum turun"
    elif macd_line > signal_line and histogram < 0:
        trend = "WEAKENING_BULL"
        desc = "Bullish tapi momentum mulai melemah"
    else:
        trend = "WEAKENING_BEAR"
        desc = "Bearish tapi momentum mulai melemah"

    return {
        "macd_line": macd_line,
        "signal_line": signal_line,
        "histogram": histogram,
        "trend": trend,
        "description": desc,
    }


def interpret_rsi(rsi: float) -> dict:
    """Terjemahkan nilai RSI jadi sinyal dan penjelasan."""
    if rsi is None:
        return {"signal": "UNKNOWN", "description": "Data RSI tidak tersedia"}
    if rsi >= 80:
        return {"signal": "STRONG_SELL", "description": f"RSI {rsi} — Sangat overbought, potensi koreksi besar"}
    elif rsi >= 70:
        return {"signal": "SELL", "description": f"RSI {rsi} — Overbought, hati-hati reversal"}
    elif rsi >= 60:
        return {"signal": "NEUTRAL_HIGH", "description": f"RSI {rsi} — Momentum positif tapi mulai panas"}
    elif rsi >= 40:
        return {"signal": "NEUTRAL", "description": f"RSI {rsi} — Zona netral, belum ada sinyal kuat"}
    elif rsi >= 30:
        return {"signal": "NEUTRAL_LOW", "description": f"RSI {rsi} — Momentum negatif tapi belum oversold"}
    elif rsi >= 20:
        return {"signal": "BUY", "description": f"RSI {rsi} — Oversold, potensi reversal naik"}
    else:
        return {"signal": "STRONG_BUY", "description": f"RSI {rsi} — Sangat oversold, peluang beli kuat"}


def get_indicators(coin: str, days: int = 30) -> dict:
    """
    Fungsi utama — ambil data dan hitung semua indikator.

    Args:
        coin : nama koin (bitcoin, ethereum, solana, dll)
        days : jumlah hari data historis (default 30)

    Returns:
        dict berisi RSI, MACD, dan interpretasinya
    """
    COIN_IDS = {
        "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
        "bnb": "binancecoin", "doge": "dogecoin", "ada": "cardano",
    }
    coin_id = COIN_IDS.get(coin.lower(), coin.lower())

    df = fetch_ohlcv(coin_id, days)
    if df.empty:
        return {"error": f"Gagal fetch data OHLCV untuk {coin}"}

    rsi = calc_rsi(df)
    macd = calc_macd(df)
    rsi_interp = interpret_rsi(rsi)

    # Gabungkan sinyal RSI + MACD
    combined = _combine_signals(rsi_interp["signal"], macd.get("trend", ""))

    return {
        "coin": coin_id,
        "data_points": len(df),
        "rsi": {
            "value": rsi,
            "signal": rsi_interp["signal"],
            "description": rsi_interp["description"],
        },
        "macd": macd,
        "combined_signal": combined["signal"],
        "combined_description": combined["description"],
    }


def _combine_signals(rsi_signal: str, macd_trend: str) -> dict:
    """Gabungkan sinyal RSI dan MACD jadi rekomendasi final."""
    bullish_rsi = rsi_signal in ("BUY", "STRONG_BUY", "NEUTRAL_LOW")
    bearish_rsi = rsi_signal in ("SELL", "STRONG_SELL", "NEUTRAL_HIGH")
    bullish_macd = macd_trend in ("BULLISH", "WEAKENING_BEAR")
    bearish_macd = macd_trend in ("BEARISH", "WEAKENING_BULL")

    if bullish_rsi and bullish_macd:
        return {"signal": "STRONG_BUY", "description": "RSI oversold + MACD bullish — konfirmasi kuat untuk beli"}
    elif bearish_rsi and bearish_macd:
        return {"signal": "STRONG_SELL", "description": "RSI overbought + MACD bearish — konfirmasi kuat untuk jual"}
    elif bullish_rsi and not bearish_macd:
        return {"signal": "BUY", "description": "RSI oversold, MACD belum konfirmasi — hati-hati tapi bullish"}
    elif bearish_rsi and not bullish_macd:
        return {"signal": "SELL", "description": "RSI overbought, MACD belum konfirmasi — mulai waspadai"}
    elif bullish_macd:
        return {"signal": "WATCH_BUY", "description": "MACD bullish tapi RSI netral — pantau peluang masuk"}
    elif bearish_macd:
        return {"signal": "WATCH_SELL", "description": "MACD bearish tapi RSI netral — pantau potensi turun"}
    else:
        return {"signal": "HOLD", "description": "Sinyal RSI dan MACD belum jelas — tunggu konfirmasi"}
