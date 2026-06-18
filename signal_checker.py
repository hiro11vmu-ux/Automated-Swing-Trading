import yfinance as yf
import requests
import os
import pandas as pd
import random
from datetime import datetime
import alpaca_trade_api as tradeapi

# =========================
# 環境変数
# =========================
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# ✅ PAPERトレード（安全）
api = tradeapi.REST(
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    base_url="https://paper-api.alpaca.markets"
)


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
# 銘柄取得（403対策）
# =========================
def get_symbols():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        html = requests.get(url, headers=headers).text
        table = pd.read_html(html)[0]
        symbols = table["Symbol"].tolist()
        return [s.replace(".", "-") for s in symbols]

    except:
        return ["AAPL", "NVDA", "MSFT", "AMZN"]


# =========================
# データ取得
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

    df["TR"] = (df["High"] - df["Low"]).abs()
    df["ATR"] = df["TR"].rolling(14).mean()

    return df


# =========================
# ファンダ
# =========================
def fundamental_check(info):
    score = 0

    if info:
        if info.get("trailingPE") and info["trailingPE"] < 30:
            score += 1
        if info.get("revenueGrowth") and info["revenueGrowth"] > 0.1:
            score += 1

    return score


# =========================
# 買いロジック
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
# 売りロジック
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
    return round(entry - df.iloc[-1]["ATR"] * 2, 2)


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

    candidates = sorted(candidates, key=lambda x: x[1], reverse=True)[:15]

    # ✅ 現在の保有銘柄取得（重複防止）
    positions = [p.symbol for p in api.list_positions()]

    for symbol, change, df, info in candidates:

        df = calc_indicators(df)

        buy_score = buy_logic(df)
        fund_score = fundamental_check(info)

        total = buy_score + fund_score
        price = df.iloc[-1]["close"]

        # =====================
        # ✅ BUY
        # =====================
        if total >= 3 and symbol not in positions:
            entry = entry_price(df)
            sl = atr_stop(df, entry)
            tp = take_profit(df)
            ts = trailing(df)

            messages.append(f"✅ BUY {symbol} {price}")

            try:
                api.submit_order(
                    symbol=symbol,
                    qty=1,
                    side="buy",
                    type="market",
                    time_in_force="day"
                )
                print(f"{symbol} BUY成功")

            except Exception as e:
                print("BUYエラー:", e)

        # =====================
        # ✅ SELL
        # =====================
        sell_signals = sell_logic(df)

        if sell_signals and symbol in positions:

            messages.append(f"⚠️ SELL {symbol}")

            try:
                api.submit_order(
                    symbol=symbol,
                    qty=1,
                    side="sell",
                    type="market",
                    time_in_force="day"
                )
                print(f"{symbol} SELL成功")

            except Exception as e:
                print("SELLエラー:", e)

        logs.append([datetime.now(), symbol, total, price])

    # ✅ ログ保存
    if logs:
        pd.DataFrame(logs, columns=["time", "symbol", "score", "price"]).to_csv(
            "trade_log.csv", index=False
        )

    # ✅ LINE通知
    if messages:
        send_line("📊 自動売買BOT\n\n" + "\n".join(messages))
    else:
        print("シグナルなし")


if __name__ == "__main__":
    main()
