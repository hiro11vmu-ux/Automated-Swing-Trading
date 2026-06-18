import requests
import os
import pandas as pd

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

# -----------------------------
# LINE送信
# -----------------------------
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
    print("LINE RESPONSE:", res.text)


# -----------------------------
# データ取得（エラー対策あり）
# -----------------------------
def get_data():
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AGIX&apikey={API_KEY}"
    r = requests.get(url).json()

    print("API response:", r)

    # エラー回避
    if "Time Series (Daily)" not in r:
        return None

    ts = r["Time Series (Daily)"]

    df = pd.DataFrame.from_dict(ts, orient="index")
    df = df.rename(columns={"4. close": "close"})
    df["close"] = df["close"].astype(float)

    df = df.sort_index()

    return df


# -----------------------------
# 指標計算
# -----------------------------
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

