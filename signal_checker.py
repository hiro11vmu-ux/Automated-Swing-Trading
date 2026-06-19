import yfinance as yf
import requests
import os
import pandas as pd
import alpaca_trade_api as tradeapi
import time
import random

# 設定
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")

def get_symbols():
    try:
        url_500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        url_400 = "https://en.wikipedia.org/wiki/List_of_S%26P_MidCap_400_companies"
        symbols_500 = pd.read_html(url_500, flavor='lxml')[0]['Symbol'].tolist()
        symbols_400 = pd.read_html(url_400, flavor='lxml')[0]['Symbol'].tolist()
        symbols = list(set([s.replace('.', '-') for s in (symbols_500 + symbols_400)]))
        return symbols
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return ["AAPL", "NVDA", "MSFT", "AMZN", "META"] # エラー時の予備リスト

def get_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period="1y")
        if df.empty: return None
        df = df.rename(columns={"Close": "close"})
        df["SMA50"] = df["close"].rolling(50).mean()
        df["SMA200"] = df["close"].rolling(200).mean()
        return df
    except: return None

def main():
    all_symbols = get_symbols()
    # 処理負荷対策のため、毎回ランダムに50銘柄を監視
    target_symbols = random.sample(all_symbols, min(50, len(all_symbols)))
    
    account = api.get_account()
    balance = float(account.cash)
    positions = {p.symbol: int(p.qty) for p in api.list_positions()}
    messages = []

    for symbol in target_symbols:
        df = get_data(symbol)
        if df is None: continue
        
        latest, prev = df.iloc[-1], df.iloc[-2]
        
        # === BUY: ゴールデンクロス ===
        if symbol not in positions and prev["SMA50"] <= prev["SMA200"] and latest["SMA50"] > latest["SMA200"]:
            qty = int((balance * 0.01) / latest["close"])
            if qty > 0:
                try:
                    api.submit_order(symbol=symbol, qty=qty, side="buy", type="market", time_in_force="day")
                    messages.append(f"✅ BUY {symbol}")
                except Exception as e: print(e)
        
        # === SELL: 10%損切り or デッドクロス ===
        elif symbol in positions:
            pos = api.get_position(symbol)
            if latest["close"] < float(pos.avg_entry_price) * 0.90 or (prev["SMA50"] >= prev["SMA200"] and latest["SMA50"] < latest["SMA200"]):
                api.submit_order(symbol=symbol, qty=positions[symbol], side="sell", type="market", time_in_force="day")
                messages.append(f"⚠️ SELL {symbol}")
        
        time.sleep(0.2) 

    if messages:
        requests.post("https://api.line.me/v2/bot/message/push", 
                      headers={"Authorization": f"Bearer {LINE_TOKEN}"}, 
                      json={"to": USER_ID, "messages": [{"type":"text","text":"\n".join(messages)}]})

if __name__ == "__main__":
    main()
