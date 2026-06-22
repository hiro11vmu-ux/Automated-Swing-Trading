import yfinance as yf
import requests
import os
import time
import random
import datetime
import pandas as pd
import ta
import pandas_market_calendars as mcal
import pytz  # 追加
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
    # UTCタイムゾーンを設定
    now = datetime.datetime.now(pytz.utc)
    schedule = nyse.schedule(start_date=now.date(), end_date=now.date())
    if schedule.empty: return False
    
    # 比較のために全てをUTCで扱う
    m_open = schedule.iloc[0].market_open
    m_close = schedule.iloc[0].market_close
    
    return m_open <= now <= m_close

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def main():
    if not is_market_open():
        print("DEBUG: 市場休場中または時間外です")
        return

    symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL"]
    try:
        positions = {p.symbol: float(p.qty) for p in client.get_all_positions()}
    except:
        positions = {}
        
    messages = []

    for symbol in symbols:
        time.sleep(random.uniform(3.0, 5.0))
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo")
        if df.empty: continue
        
        df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
        macd = ta.trend.MACD(df["Close"])
        df["MACD"] = macd.macd()
        df["Signal"] = macd.macd_signal()
        
        latest = df.iloc[-1]
        
        if symbol not in positions and latest["RSI"] < 40 and latest["MACD"] > latest["Signal"]:
            client.submit_order(MarketOrderRequest(symbol=symbol, qty=1, side=OrderSide.BUY, timeInForce=TimeInForce.DAY))
            messages.append(f"✅ BUY {symbol}")
        
        elif symbol in positions:
            pos = client.get_open_position(symbol)
            avg_entry = float(pos.avg_entry_price)
            if float(latest["Close"]) <= avg_entry * 0.95:
                client.close_position(symbol)
                messages.append(f"⚠️ SELL (Trailing Stop) {symbol}")

    if messages: send_line("\n".join(messages))

if __name__ == "__main__":
    main()
