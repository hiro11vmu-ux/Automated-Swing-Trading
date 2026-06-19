import yfinance as yf
import requests
import os
import pandas as pd
import random
import alpaca_trade_api as tradeapi

# 設定
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

# LINE通知
def send_line(msg):
    if not LINE_TOKEN:
        return
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {LINE_TOKEN}"},
        json={"to": USER_ID, "messages": [{"type":"text","text":msg}]}
    )

# 銘柄リスト
def get_symbols():
    return ["AAPL","NVDA","MSFT","AMZN","META","TSLA"]

# データ取得
def get_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period="3mo")
        if df.empty: return None
        df = df.rename(columns={"Close": "close", "High": "high", "Low": "low", "Open": "open", "Volume": "volume"})
        df["SMA20"] = df["close"].rolling(20).mean()
        df["SMA50"] = df["close"].rolling(50).mean()
        df["RSI"] = 100 - (100 / (1 + df["close"].diff().clip(lower=0).rolling(14).mean() / df["close"].diff().clip(upper=0).abs().rolling(14).mean()))
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df["ATR"] = (df["high"] - df["low"]).rolling(14).mean()
        return df
    except:
        return None

# 購入シグナル判定
def buy_signal(df):
    latest = df.iloc[-1]
    return latest["RSI"] < 40 and latest["SMA20"] > latest["SMA50"]

# 売却シグナル判定
def sell_signal(df):
    latest = df.iloc[-1]
    return latest["RSI"] > 70

# 購入数計算
def calc_qty(balance, entry, stop):
    risk = balance * 0.02
    return int(risk / (entry - stop)) if (entry - stop) > 0 else 1

def main():
    symbols = get_symbols()
    account = api.get_account()
    balance = float(account.equity)
    positions = {p.symbol: int(p.qty) for p in api.list_positions()}
    messages = []

    for symbol in symbols:
        df = get_data(symbol)
        if df is None: continue
        
        price = df.iloc[-1]["close"]
        atr = df.iloc[-1]["ATR"]
        entry = price
        stop = price - atr * 2

        # === BUY ===
        if buy_signal(df) and symbol not in positions:
            qty = calc_qty(balance, entry, stop)
            try:
                api.submit_order(symbol=symbol, qty=qty, side="buy", type="market", time_in_force="day")
                messages.append(f"✅ BUY {symbol} x{qty}")
            except Exception as e:
                print(e)

        # === SELL ===
        if symbol in positions:
            pos = api.get_position(symbol)
            avg_price = float(pos.avg_entry_price)
            
            # 【追加】10%損切りルール
            if price < avg_price * 0.90:
                api.submit_order(symbol=symbol, qty=positions[symbol], side="sell", type="market", time_in_force="day")
                messages.append(f"🚨 STOP LOSS {symbol} (10% cut)")
                continue

            # 通常売り
            if sell_signal(df):
                api.submit_order(symbol=symbol, qty=positions[symbol], side="sell", type="market", time_in_force="day")
                messages.append(f"⚠️ SELL {symbol}")

            # トレーリング
            highest = df["close"].rolling(10).max().iloc[-1]
            if price < highest * 0.95:
                api.submit_order(symbol=symbol, qty=positions[symbol], side="sell", type="market", time_in_force="day")
                messages.append(f"📉 TRAIL {symbol}")

    if messages:
        send_line("\n".join(messages))

if __name__ == "__main__":
    main()
