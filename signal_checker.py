import yfinance as yf
import requests
import os
import time
import random
import datetime
import pandas as pd
import ta
import pandas_market_calendars as mcal
import pytz
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# 設定
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

client = TradingClient(API_KEY, SECRET_KEY, paper=True)

def get_symbols():
    # 5行目(header=4)から読み込み、Shift-JISで解析
    df = pd.read_csv("holdings.csv", header=4, encoding='shift_jis')
    
    # 2列目(Ticker列)を確実に指定して抽出
    ticker_col = df.columns[1] 
    all_symbols = df[ticker_col].dropna().astype(str).tolist()
    
    # 不要な記号や無効なデータを徹底的に除外
    exclude_list = ["SPSM", "US DOLLAR", "-", "nan", "Ticker"]
    all_symbols = [s.strip() for s in all_symbols if s not in exclude_list and not s.startswith("E-MINI") and len(s) > 0]
    
    # 50銘柄ランダム抽出
    return random.sample(all_symbols, min(len(all_symbols), 50))

def is_market_open():
    nyse = mcal.get_calendar('NYSE')
    now = datetime.datetime.now(pytz.utc)
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
    
    try:
        symbols = get_symbols()
        positions = {p.symbol: float(p.qty) for p in client.get_all_positions()}
    except Exception as e:
        print(f"Error in init: {e}")
        return
        
    messages = []
    for symbol in symbols:
        time.sleep(random.uniform(1.0, 2.0))
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="6mo")
            if df.empty: continue
            
            df["RSI"] = ta.momentum.rsi(df["Close"], window=14)
            macd = ta.trend.MACD(df["Close"])
            df["MACD"] = macd.macd()
            df["Signal"] = macd.macd_signal()
            latest = df.iloc[-1]
            
            if symbol not in positions and latest["RSI"] < 40 and latest["MACD"] > latest["Signal"]:
                client.submit_order(MarketOrderRequest(symbol=symbol, qty=1, side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
                messages.append(f"✅ BUY {symbol}")
            elif symbol in positions:
                pos = client.get_open_position(symbol)
                if float(latest["Close"]) <= float(pos.avg_entry_price) * 0.95:
                    client.close_position(symbol)
                    messages.append(f"⚠️ SELL (Trailing Stop) {symbol}")
        except Exception:
            continue

    if messages: send_line("\n".join(messages))

if __name__ == "__main__":
    main()
