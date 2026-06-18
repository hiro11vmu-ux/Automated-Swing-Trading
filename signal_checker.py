import yfinance as yf
import requests
import os
import pandas as pd
import random
import alpaca_trade_api as tradeapi

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    print("❌ APIキー未設定")
    exit()

api = tradeapi.REST(
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    base_url="https://paper-api.alpaca.markets"
)

# =====================
# LINE
# =====================
def send_line(msg):
    if not LINE_TOKEN:
        return
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {LINE_TOKEN}"},
        json={"to": USER_ID, "messages": [{"type":"text","text":msg}]}
    )

# =====================
# 銘柄
# =====================
def get_symbols():
    return ["AAPL","NVDA","MSFT","AMZN","META","TSLA"]

# =====================
# データ
# =====================
def get_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period="3mo")
        if df.empty:
            return None
        df = df.rename(columns={"Close":"close"})
        return df
    except:
        return None

# =====================
# 指標
# =====================
def calc(df):
    df["SMA20"] = df["close"].rolling(20).mean()
    df["SMA50"] = df["close"].rolling(50).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["TR"] = (df["High"] - df["Low"]).abs()
    df["ATR"] = df["TR"].rolling(14).mean()

    return df

# =====================
# ロジック
# =====================
def buy_signal(df):
    latest = df.iloc[-1]
    return latest["RSI"] < 40 and latest["SMA20"] > latest["SMA50"]

def sell_signal(df):
    latest = df.iloc[-1]
    return latest["RSI"] > 70 or latest["close"] < latest["SMA20"]

# =====================
# 資金管理（超重要）
# =====================
def calc_qty(balance, entry, stop):
    risk = balance * 0.02
    risk_per_share = abs(entry - stop)
    if risk_per_share == 0:
        return 0
    return max(int(risk / risk_per_share), 1)

# =====================
# MAIN
# =====================
def main():
    print("🚀 START")

    account = api.get_account()
    balance = float(account.cash)

    positions = {p.symbol: float(p.qty) for p in api.list_positions()}

    messages = []

    for symbol in get_symbols():

        df = get_data(symbol)
        if df is None or len(df) < 50:
            continue

        df = calc(df)

        price = df.iloc[-1]["close"]
        atr = df.iloc[-1]["ATR"]

        entry = price
        stop = price - atr * 2

        # === BUY ===
        if buy_signal(df) and symbol not in positions:
            qty = calc_qty(balance, entry, stop)

            try:
                api.submit_order(symbol=symbol, qty=qty, side="buy",
                                 type="market", time_in_force="day")

                print(f"✅ BUY {symbol}")
                messages.append(f"✅ BUY {symbol} x{qty}")

            except Exception as e:
                print(e)

        # === SELL ===
        if symbol in positions:

            # 通常売り
            if sell_signal(df):
                try:
                    api.submit_order(symbol=symbol, qty=positions[symbol],
                                     side="sell", type="market", time_in_force="day")
                    messages.append(f"⚠️ SELL {symbol}")
                except:
                    pass

            # トレーリング
            highest = df["close"].rolling(10).max().iloc[-1]
            if price < highest * 0.95:
                try:
                    api.submit_order(symbol=symbol, qty=positions[symbol],
                                     side="sell", type="market", time_in_force="day")
                    messages.append(f"📉 TRAIL {symbol}")
                except:
                    pass

    if messages:
        send_line("\n".join(messages))
    else:
        print("シグナルなし")

if __name__ == "__main__":
    main()
