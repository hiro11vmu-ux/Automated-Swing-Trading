import yfinance as yf
import requests
import os
import pandas as pd

# =============================
# 環境変数
# =============================
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

# ✅ スキャン対象（市場代表）
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

    res = requests.post(url, headers=headers, json=data)
    print("LINE STATUS:", res.status_code)


# =============================
# データ取得（株価＋ファンダ）
# =============================
def get_data(symbol):
    stock = yf.Ticker(symbol)

    df = stock.history(period="3mo")

    if df is None or df.empty:
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
# ファンダ
# =============================
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


# =============================
# テクニカル（買い）
# =============================
def buy_logic(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0

    # SMA（トレンド）
    if latest["SMA20"] > latest["SMA50"]:
        score += 1

    # RSI
    if latest["RSI"] < 35:
        score += 1

    # MACDクロス
    if prev["MACD"] <= prev["Signal"] and latest["MACD"] > latest["Signal"]:
        score += 2

    return score


# =============================
# 売り（利確・反転）
# =============================
def sell_logic(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signals = []

    # RSI過熱
    if latest["RSI"] > 70:
        signals.append("RSI過熱")

    # MACDデッドクロス
    if prev["MACD"] >= prev["Signal"] and latest["MACD"] < latest["Signal"]:
        signals.append("MACDデッドクロス")

    # トレンド崩壊
    if latest["close"] < latest["SMA20"]:
        signals.append("SMA割れ")

    return signals


# =============================
# エントリー（指値）
# =============================
def calculate_entry(df):
    latest = df.iloc[-1]
    return round(latest["SMA20"], 2)


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

        buy_score = buy_logic(df)
        fund_score = fundamental_check(info)

        total = buy_score + fund_score

        price = df.iloc[-1]["close"]
        entry = calculate_entry(df)

        # ✅ 買い候補
        if total >= 3:
            messages.append(
                f"""✅ 買い候補
{symbol}
現在価格: {round(price, 2)}
指値目安: {entry}
スコア: {total}
"""
            )

        # ✅ 売りシグナル
        sell_signals = sell_logic(df)

        if sell_signals:
            messages.append(
                f"""⚠️ 売りシグナル
{symbol}
現在価格: {round(price, 2)}
理由: {", ".join(sell_signals)}
"""
            )

    if messages:
        send_line("📊 市場スキャン結果\n\n" + "\n".join(messages))
    else:
        print("シグナルなし")


if __name__ == "__main__":
    main()
