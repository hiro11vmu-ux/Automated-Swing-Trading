import yfinance as yf
import requests
import os
import pandas as pd
import time
import random
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
    try:
        url_500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        url_400 = "https://en.wikipedia.org/wiki/List_of_S%26P_MidCap_400_companies"
        s500 = pd.read_html(url_500, flavor='lxml')[0]['Symbol'].tolist()
        s400 = pd.read_html(url_400, flavor='lxml')[0]['Symbol'].tolist()
        symbols = list(set([s.replace('.', '-') for s in (s500 + s400)]))
        return symbols
    except:
        return ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL"]

def main():
    all_symbols = get_symbols()
    # 監視銘柄を10社に絞る
    num_to_sample = min(10, len(all_symbols))
    symbols = random.sample(all_symbols, num_to_sample)
    
    try:
        balance = float(client.get_account().cash)
    except:
        return

    positions = {p.symbol: float(p.qty) for p in client.get_all_positions()}
    messages = []

    for symbol in symbols:
        df = yf.Ticker(symbol).history(period="1y")
        if df.empty: continue
        
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["SMA200"] = df["Close"].rolling(200).mean()
        latest, prev = df.iloc[-1], df.iloc[-2]
        price = float(latest["Close"])

        # BUY: 資金の10%で端株購入
        if symbol not in positions and prev["SMA50"] <= prev["SMA200"] and latest["SMA50"] > latest["SMA200"]:
            qty = round((balance * 0.10) / price, 4)
            if qty > 0:
                client.submit_order(MarketOrderRequest(symbol=symbol, qty=qty, side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
                messages.append("✅ BUY " + symbol + " (qty: " + str(qty) + ")")
        
        # SELL
        elif symbol in positions:
            try:
                pos = client.get_open_position(symbol)
                if price < float(pos.avg_entry_price) * 0.90 or (prev["SMA50"] >= prev["SMA200"] and latest["SMA50"] < latest["SMA200"]):
                    client.close_position(symbol)
                    messages.append("⚠️ SELL " + symbol)
            except: pass
        
        time.sleep(0.5)

    if messages:
        requests.post("https://api.line.me/v2/bot/message/push", 
                      headers={"Authorization": "Bearer " + LINE_TOKEN}, 
                      json={"to": USER_ID, "messages": [{"type":"text","text":"\n".join(messages)}]})

if __name__ == "__main__":
    main()
