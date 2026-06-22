import yfinance as yf
import requests
import os
import time
import random
import datetime
import pandas as pd
import pandas_ta as ta
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
    nyse = mcal.get_calendar('NYSE')
    now = datetime.datetime.now()
    schedule = nyse.schedule(start_date=now.date(), end_date=now.date())
    if schedule.empty: return False
    return schedule.iloc[0].market_open <= now <= schedule.iloc[0].market_close

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def main():
    if not is_market_open(): return

    symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL"]
    positions = {p.symbol: float(p.qty) for p in client.get_all_positions()}
    messages = []

    for symbol in symbols:
        time.sleep(random.uniform(3.0, 5.0))
        df = yf.Ticker(symbol).history(period="6mo")
        if df.empty: continue
        
        # 指標計算
        df["RSI"] = ta.rsi(df["Close"], length=14)
        macd = ta.macd(df["Close"])
        df["MACD"] = macd.iloc[:, 0]
        df["Signal"] = macd.iloc[:, 2]
        
        latest = df.iloc[-1]
        
        # 買い条件: RSI < 40 かつ MACDゴールデンクロス
        if symbol not in positions and latest["RSI"] < 40 and latest["MACD"] > latest["Signal"]:
            client.submit_order(MarketOrderRequest(symbol=symbol, qty=1, side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
            messages.append(f"✅ BUY {symbol}")
        
        # 売り条件: トレーリングストップ (-5%)
        elif symbol in positions:
            pos = client.get_open_position(symbol)
            avg_entry = float(pos.avg_entry_price)
            # 現在値が買値から5%下落したら決済
            if float(latest["Close"]) <= avg_entry * 0.95:
                client.close_position(symbol)
                messages.append(f"⚠️ SELL (Trailing Stop) {symbol}")

    if messages: send_line("\n".join(messages))

if __name__ == "__main__":
    main()
