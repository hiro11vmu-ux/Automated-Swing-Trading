import yfinance as yf
import requests
import os
import pandas as pd
import time
import random
import datetime
import pandas_market_calendars as mcal
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# 設定
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

client = TradingClient(API_KEY, SECRET_KEY, paper=True)

def is_market_open():
    """米国市場が現在開いているか判定"""
    nyse = mcal.get_calendar('NYSE')
    now = datetime.datetime.now()
    schedule = nyse.schedule(start_date=now.date(), end_date=now.date())
    if schedule.empty: return False
    
    # 取引時間内か判定
    market_open = schedule.iloc[0].market_open.replace(tzinfo=None)
    market_close = schedule.iloc[0].market_close.replace(tzinfo=None)
    return market_open <= now <= market_close

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def main():
    if not is_market_open():
        print("DEBUG: 市場休場中または取引時間外です。")
        return

    print("DEBUG: ボット開始")
    symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL"]
    
    try:
        balance = float(client.get_account().cash)
    except Exception as e:
        return

    positions = {p.symbol: float(p.qty) for p in client.get_all_positions()}
    messages = []

    for symbol in symbols:
        time.sleep(random.uniform(5.0, 8.0))
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty: continue
        
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["SMA200"] = df["Close"].rolling(200).mean()
        latest, prev = df.iloc[-1], df.iloc[-2]
        price = float(latest["Close"])

        if symbol not in positions and prev["SMA50"] <= prev["SMA200"] and latest["SMA50"] > latest["SMA200"]:
            qty = round((balance * 0.10) / price, 4)
            if qty > 0:
                client.submit_order(MarketOrderRequest(symbol=symbol, qty=qty, side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
                messages.append(f"✅ BUY {symbol}")
        elif symbol in positions:
            pos = client.get_open_position(symbol)
            if price < float(pos.avg_entry_price) * 0.90 or (prev["SMA50"] >= prev["SMA200"] and latest["SMA50"] < latest["SMA200"]):
                client.close_position(symbol)
                messages.append(f"⚠️ SELL {symbol}")

    if messages:
        send_line("【取引通知】\n" + "\n".join(messages))

if __name__ == "__main__":
    main()
