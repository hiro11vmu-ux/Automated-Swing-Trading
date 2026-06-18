print("🔥 THIS IS NEW CODE 🔥")
import requests
import os
import pandas as pd

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

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

def get_data():
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AGIX&apikey={API_KEY}"
    r = requests.get(url).json()
    ts = r["Time Series (Daily)"]

    df = pd.DataFrame.from_dict(ts, orient="index")
    df = df.rename(columns={"4. close": "close"})
    df["close"] = df["close"].astype(float)
    df = df.sort_index()

    return df

def calc_indicators(df):
    df["SMA20"] = df["close"].rolling(20).mean()
    df["SMA50"] = df["close"].rolling(50).mean()

    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    return df

def signal_logic(df):
    latest = df.iloc[-1]
    score = 0

    if latest["SMA20"] > latest["SMA50"]:
        score += 1
        sma = "強気"
    else:
        sma = "弱気"

    if latest["RSI"] < 30:
        score += 1
        rsi = "買い"
    elif latest["RSI"] > 70:
        rsi = "売り"
    else:
        rsi = "中立"

    if latest["MACD"] > latest["Signal"]:
        score += 1
        macd = "強気"
    else:
        macd = "弱気"

    if score >= 2:
        final = "✅ 買い"
    elif score == 1:
        final = "⚖️ 中立"
    else:
        final = "❌ 売り"

    return final, sma, rsi, macd, latest["close"]

def main():
    df = get_data()
    df = calc_indicators(df)

    final, sma, rsi, macd, price = signal_logic(df)

    message = f"""
📊 AGIX シグナル

現在価格: {round(price,2)}

総合判定: {final}

SMA: {sma}
RSI: {rsi}
MACD: {macd}
"""

    send_line(message)

if __name__ == "__main__":
    main()
