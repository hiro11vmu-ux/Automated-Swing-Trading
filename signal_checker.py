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

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"DEBUG: LINE送信エラー: {e}")

def get_symbols():
    return ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL"]

def main():
    print("DEBUG: ボット開始")
    symbols = get_symbols()
    
    try:
        balance = float(client.get_account().cash)
    except Exception as e:
        print(f"DEBUG: Alpacaエラー: {e}")
        return

    positions = {p.symbol: float(p.qty) for p in client.get_all_positions()}
    messages = []

    for symbol in symbols:
        print(f"DEBUG: {symbol} 解析中...")
        try:
            time.sleep(random.uniform(5.0, 8.0))
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1y")
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
                pos = client.get_open_position(symbol)
                if price < float(pos.avg_entry_price) * 0.90 or (prev["SMA50"] >= prev["SMA200"] and latest["SMA50"] < latest["SMA200"]):
                    client.close_position(symbol)
                    messages.append(f"⚠️ SELL {symbol}")
        
        except Exception as e:
            print(f"DEBUG: {symbol} 処理中にエラー: {e}")
            continue

    # 通知ロジック：取引があればそれを、なければ稼働確認を送る
    if messages:
        send_line("【取引通知】\n" + "\n".join(messages))
    else:
        send_line("【ボット稼働確認】\n本日の監視完了。現在条件に合致する銘柄はありません。")

if __name__ == "__main__":
    main()
