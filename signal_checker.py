import requests
import os
import pandas as pd

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")


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

    res = requests.post(url, headers=headers, json=data)
    print("LINE:", res.status_code)


# =============================
# データ取得
# =============================
def get_data():
    symbol = "AAPL"

    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}"
    r = requests.get(url).json()

    if "Time Series (Daily)" not in r:
        return None

    df = pd.DataFrame.from_dict(r["Time Series (Daily)"], orient="index")
    df["close"] = df["4. close"].astype(float)
    df = df.sort_index()

    return df


# =============================
# 指標計算
# =============================
def calc_indicators(df):
    # SMA
    df["SMA20"] = df["close"].rolling(20).mean()
    df["SMA50"] = df["close"].rolling(50).mean()

    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    return df


# =============================
# シグナル判定
# =============================
def signal_logic(df):
    latest = df.iloc[-1]

    score = 0

    # SMA
    if latest["SMA20"] > latest["SMA50"]:
        sma = "強気"
        score += 1
    else:
        sma = "弱気"

    # RSI
    if latest["RSI"] < 30:
        rsi = "買い"
        score += 1
    elif latest["RSI"] > 70:
        rsi = "売り"
    else:
        rsi = "中立"

    # MACD
    if latest["MACD"] > latest["Signal"]:
        macd = "強気"
        score += 1
    else:
        macd = "弱気"

    # 総合判定
    if score >= 2:
        final = "✅ 買い"
    elif score == 1:
        final = "⚖️ 中立"
    else:
        final = "❌ 売り"

    return final, sma, rsi, macd, latest["close"]


# =============================
# MAIN
# =============================
def main():
    df = get_data()

    if df is None:
        send_line("❌ データ取得失敗")
        return

    df = calc_indicators(df)

    final, sma, rsi, macd, price = signal_logic(df)

    message = f"""
📊 AAPL シグナル

現在価格: {round(price,2)}

総合判定: {final}

SMA: {sma}
RSI: {rsi}
MACD: {macd}
"""

    send_line(message)


if __name__ == "__main__":
    main()
``
