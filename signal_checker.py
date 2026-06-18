import requests
import os
import pandas as pd

# =============================
# 環境変数
# =============================
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
    print("LINE STATUS:", res.status_code)


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
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    return df


# =============================
# シグナル判定（強化版）
# =============================
def signal_logic(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0

    # SMA
    if latest["SMA20"] > latest["SMA50"]:
        sma = "強気"
        score += 1
    else:
        sma = "弱気"

    # RSI
    if latest["RSI"] < 30:
        rsi = "強い買い"
        score += 2
    elif latest["RSI"] > 70:
        rsi = "強い売り"
        score -= 2
    else:
        rsi = "中立"

    # MACDクロス
    if prev["MACD"] <= prev["Signal"] and latest["MACD"] > latest["Signal"]:
        macd = "ゴールデンクロス🔥"
        score += 2
    elif prev["MACD"] >= prev["Signal"] and latest["MACD"] < latest["Signal"]:
        macd = "デッドクロス❌"
        score -= 2
    else:
        macd = "継続"

    # 総合判定
    if score >= 3:
        final = "✅ 強い買い"
    elif score <= -3:
        final = "❌ 強い売り"
    else:
        final = "なし"

    return final, sma, rsi, macd, latest["close"], score


# =============================
# メイン
# =============================
def main():
    print("🚀 START")

    df = get_data()

    if df is None:
        send_line("❌ データ取得失敗")
        return

    df = calc_indicators(df)

    final, sma, rsi, macd, price, score = signal_logic(df)

    # ✅ 強い時だけ通知
    if final == "なし":
        print("スキップ（弱いシグナル）")
        return

    message = f"""
📊 AAPL 強シグナル

現在価格: {round(price, 2)}

スコア: {score}

判定: {final}

SMA: {sma}
RSI: {rsi}
MACD: {macd}
"""

    send_line(message)


if __name__ == "__main__":
    main()
