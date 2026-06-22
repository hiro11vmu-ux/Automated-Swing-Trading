import yfinance as yf
import requests
import os
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
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": USER_ID, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, json=payload)

def main():
    print("DEBUG: ボット開始")
    symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL"]
    
    # ポジションと残高の取得
    try:
        balance = float(client.get_account().cash)
        positions = {p.symbol: float(p.qty) for p in client.get_all_positions()}
    except Exception as e:
        print(f"DEBUG: Alpacaエラー: {e}")
        return

    messages = []
    
    # 売買ロジック
    for symbol in symbols:
        time.sleep(random.uniform(2.0, 4.0)) # 負荷軽減
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty: continue
        
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["SMA200"] = df["Close"].rolling(200).mean()
        latest, prev = df.iloc[-1], df.iloc[-2]
        price = float(latest["Close"])

        # 買い条件（ゴールデンクロス）
        if symbol not in positions and prev["SMA50"] <= prev["SMA200"] and latest["SMA50"] > latest["SMA200"]:
            qty = round((balance * 0.10) / price, 4)
            client.submit_order(MarketOrderRequest(symbol=symbol, qty=qty, side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
            messages.append(f"✅ BUY {symbol}")
        
        # 売り条件
        elif symbol in positions:
            pos = client.get_open_position(symbol)
            if price < float(pos.avg_entry_price) * 0.90 or (prev["SMA50"] >= prev["SMA200"] and latest["SMA50"] < latest["SMA200"]):
                client.close_position(symbol)
                messages.append(f"⚠️ SELL {symbol}")

    # 通知処理
    if messages:
        send_line("【取引通知】\n" + "\n".join(messages))
    else:
        # 生存確認：30分に1回通知されるのがうるさい場合は、ここはコメントアウトしてください
        send_line("【ボット稼働中】\n条件合致なし。監視を継続しています。")

if __name__ == "__main__":
    main()
