import yfinance as yf
import requests
import os
import pandas as pd
import time
import random
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# 設定（GitHubのSecretsから取得）
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

client = TradingClient(API_KEY, SECRET_KEY, paper=True)

def send_line(message):
    """Messaging APIを使ってLINEにプッシュ通知を送る"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"DEBUG: LINE通知結果: {response.status_code}, {response.text}")

def get_symbols():
    return ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "TSLA", "META", "AMD", "NFLX", "INTC"]

def main():
    print("DEBUG: ボット開始")
    symbols = get_symbols()
    
    try:
        balance = float(client.get_account().cash)
    except Exception as e:
        print(f"DEBUG: Alpaca接続エラー: {e}")
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

        # BUY条件
        if symbol not in positions and prev["SMA50"] <= prev["SMA200"] and latest["SMA50"] > latest["SMA200"]:
            qty = round((balance * 0.10) / price, 4)
            if qty > 0:
                client.submit_order(MarketOrderRequest(symbol=symbol, qty=qty, side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
                messages.append(f"✅ BUY {symbol}")
        
        # SELL条件
        elif symbol in positions:
            try:
                pos = client.get_open_position(symbol)
                if price < float(pos.avg_entry_price) * 0.90 or (prev["SMA50"] >= prev["SMA200"] and latest["SMA50"] < latest["SMA200"]):
                    client.close_position(symbol)
                    messages.append(f"⚠️ SELL {symbol}")
            except: pass

    if messages:
        send_line("\n".join(messages))
    else:
        print("DEBUG: 取引条件に合致なし")

if __name__ == "__main__":
    main()
