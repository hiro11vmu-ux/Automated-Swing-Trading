import yfinance as yf
import requests
import os
import pandas as pd

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

SYMBOLS = ["NVDA", "AAPL", "MSFT", "AMZN", "META"]


# =============================
# LINE送信
# =============================
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


# =============================
# データ取得（株価＋ファンダ）
# =============================
def get_data(symbol):
    stock = yf.Ticker(symbol)

    df = stock.history(period="3mo")

    if df.empty:
        return None, None

    df = df.rename(columns={"Close": "close"})

    info = stock.info

    return df, info


# =============================
# 指標
# =============================
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

    return df


# =============================
# ファンダ判定
# =============================
def fundamental_check(info):
    try:
        pe = info.get("trailingPE", None)
        growth = info.get("revenueGrowth", None)

        score = 0

        if pe and pe < 30:
            score += 1

        if growth and growth > 0.1:
            score += 1

        return score

    except:
        return 0


# =============================
# テクニカル判定
# =============================
def technical_check(df):
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


# =============================
# 指値（買いポイント）
# =============================
def calculate_entry(df):
    latest = df.iloc[-1]

    # ✅ 押し目（SMA20付近）
    entry = latest["SMA20"]

    return round(entry, 2)


# =============================
# MAIN
# =============================
def main():
    messages = []

    for symbol in SYMBOLS:
        df, info = get_data(symbol)

        if df is None or len(df) < 50:
            continue

        df = calc_indicators(df)

        tech_score = technical_check(df)
        fund_score = fundamental_check(info)

        total = tech_score + fund_score

        # ✅ 厳選
        if total >= 3:
            price = df.iloc[-1]["close"]
            entry = calculate_entry(df)

            messages.append(
                f"""
{symbol}

現在価格: {round(price,2)}
指値目安: {entry}

テク: {tech_score}
ファンダ: {fund_score}

総合: ✅ 買い候補
"""
            )

    if messages:
        send_line("📊 厳選銘柄\n\n" + "\n".join(messages))
    else:
        print("対象なし")


if __name__ == "__main__":
    main()
``
