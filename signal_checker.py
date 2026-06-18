import yfinance as yf
import requests
import os
import pandas as pd
import random
from datetime import datetime

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")


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

    res = requests.post(url, headers=headers, json=data)
    print("LINE STATUS:", res.status_code)


# =========================
# 銘柄取得（403対策）
# =========================
def get_symbols():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        html = requests.get(url, headers=headers).text
        table = pd.read_html(html)[0]

        symbols = table["Symbol"].tolist()
        symbols = [s.replace(".", "-") for s in symbols]

        return symbols

    except Exception as e:
        print("銘柄取得エラー:", e)

        # ✅ フォールバック（落ちない設計）
        return ["AAPL", "MSFT", "NVDA", "AMZN", "META"]


# =========================
# データ
# =========================
def get_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="3mo")

        if df is None or df.empty:
            return None, None

        df = df.rename(columns={"Close": "close"})
        return df, stock.info

    except:
        return None, None


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

    # ✅ ATR
    df["TR"] = (df["High"] - df["Low"]).abs()
    df["ATR"] = df["TR"].rolling(14).mean()

    return df


# =========================
# ファンダ
# =========================
def fundamental_check(info):
    score = 0

    try:
        if info:
            if info.get("trailingPE") and info["trailingPE"] < 30:
                score += 1

            if info.get("revenueGrowth") and info["revenueGrowth"] > 0.1:
                score += 1
    except:
        pass

    return score


# =========================
# 買い
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
# 売り
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
# 戦略
# =========================
def entry_price(df):
    return round(df.iloc[-1]["SMA20"], 2)


def atr_stop(df, entry):
    atr = df.iloc[-1]["ATR"]
    return round(entry - atr * 2, 2)


def take_profit(df):
    return round(df["close"].rolling(20).max().iloc[-1], 2)


def trailing(df):
    return round(df["close"].rolling(10).max().iloc[-1] * 0.95, 2)


# =========================
# MAIN
# =========================
def main():
    print("🚀 START")

    messages = []
    logs = []

    symbols = get_symbols()

    # ✅ 安全処理
    if len(symbols) > 50:
        symbols = random.sample(symbols, 50)

    candidates = []

    # ✅ 動いてる銘柄抽出
    for symbol in symbols:
        df, info = get_data(symbol)

        if df is None or len(df) < 20:
            continue

        try:
            change = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5]
            candidates.append((symbol, change, df, info))
        except:
            continue

    # ✅ 上位抽出
    candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:15]

    for symbol, change, df, info in candidates:

        df = calc_indicators(df)

        buy_score = buy_logic(df)
        fund_score = fundamental_check(info)

        total = buy_score + fund_score
        price = df.iloc[-1]["close"]

        # ✅ BUY
        if total >= 3:
            entry = entry_price(df)
            sl = atr_stop(df, entry)
            tp = take_profit(df)
            ts = trailing(df)

            messages.append(
                f"""✅ 買い候補
{symbol}

価格: {round(price,2)}
指値: {entry}

🎯 利確: {tp}
🛑 損切り: {sl}
📈 TS: {ts}
"""
            )

            logs.append([datetime.now(), symbol, "BUY", price])

        # ✅ SELL
        sell_signals = sell_logic(df)

        if sell_signals:
            messages.append(
                f"""⚠️ 売り
{symbol}

価格: {round(price,2)}
理由: {", ".join(sell_signals)}
"""
            )

            logs.append([datetime.now(), symbol, "SELL", price])

    # ✅ ログ保存
    if logs:
        pd.DataFrame(logs, columns=["time", "symbol", "type", "price"]).to_csv(
            "trade_log.csv", index=False
        )

    # ✅ LINE
    if messages:
        send_line("📊 市場スキャン結果\n\n" + "\n".join(messages))
    else:
        print("シグナルなし")


# =========================
# 実行
# =========================
if __name__ == "__main__":
    main()
