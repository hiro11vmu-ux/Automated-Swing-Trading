import yfinance as yf
import requests
import os
import pandas as pd

# =========================
# 環境変数
# =========================
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

# ✅ スキャン銘柄
SYMBOLS = ["NVDA", "AAPL", "MSFT", "AMZN", "META"]


# =========================
# LINE送信
# =========================
def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": message}]
    }

    requests.post(url, headers=headers, json=data)


# =========================
# データ取得
# =========================
def get_data(symbol):
    stock = yf.Ticker(symbol)

    df = stock.history(period="3mo")

    if df is None or df.empty:
        return None, None

    df = df.rename(columns={"Close": "close"})
    info = stock.info

    return df, info


# =========================
# 指標
# =========================
def calc_indicators(df):
    df["SMA20"] = df["close"].rolling(20).mean()
    df["SMA50"] = df["close"].rolling(50).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    # ✅ ATR（プロ損切り）
    df["high"] = df["High"]
    df["low"] = df["Low"]
    df["tr"] = (df["high"] - df["low"]).abs()
    df["ATR"] = df["tr"].rolling(14).mean()

    return df


# =========================
# ファンダ
# =========================
def fundamental_check(info):
    score = 0

    if info is None:
        return 0

    pe = info.get("trailingPE")
    growth = info.get("revenueGrowth")

    if pe and pe < 30:
        score += 1

    if growth and growth > 0.1:
        score += 1

    return score


# =========================
# 買い判定
# =========================
def buy_logic(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0

    if latest["SMA20"] > latest["SMA50"]:
        score += 1

    if latest["RSI"] < 35:
        score += 1

    if prev["MACD"] <= prev["Signal"] and latest["MACD"] > latest["Signal"]:
        score += 2

    return score


# =========================
# 売り判定
# =========================
def sell_logic(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signals = []

    if latest["RSI"] > 70:
        signals.append("RSI過熱")

    if prev["MACD"] >= prev["Signal"] and latest["MACD"] < latest["Signal"]:
        signals.append("MACDデッドクロス")

    if latest["close"] < latest["SMA20"]:
        signals.append("SMA割れ")

    return signals


# =========================
# エントリー
# =========================
def entry_price(df):
    return round(df.iloc[-1]["SMA20"], 2)


# =========================
# ATR損切り
# =========================
def atr_stop(df, entry):
    atr = df.iloc[-1]["ATR"]
    return round(entry - (atr * 2), 2)


# =========================
# 利確
# =========================
def take_profit(df):
    return round(df["close"].rolling(20).max().iloc[-1], 2)


# =========================
# トレーリング
# =========================
def trailing(df):
    return round(df["close"].rolling(10).max().iloc[-1] * 0.95, 2)


# =========================
# MAIN
# =========================
def main():
    messages = []

    for symbol in SYMBOLS:
        df, info = get_data(symbol)

        if df is None or len(df) < 50:
            continue

        df = calc_indicators(df)

        buy_score = buy_logic(df)
        fund_score = fundamental_check(info)

        total = buy_score + fund_score

        price = df.iloc[-1]["close"]

        # ✅ 買い
        if total >= 3:
            entry = entry_price(df)
            sl = atr_stop(df, entry)
            tp = take_profit(df)
            ts = trailing(df)

            messages.append(
                f"""✅ 買い候補
{symbol}

現在価格: {round(price,2)}
指値: {entry}

