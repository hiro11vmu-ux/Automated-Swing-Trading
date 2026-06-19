import yfinance as yf
import requests
import os
import pandas as pd
import alpaca_trade_api as tradeapi
import time

# 設定
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")

def get_symbols():
    # S&P 500 と S&P 400 (MidCap) を取得
    url_500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    url_400 = "https://en.wikipedia.org/wiki/List_of_S%26P_MidCap_400_companies"
    
    symbols = pd.read_html(url_500)[0]['Symbol'].tolist()
    symbols.extend(pd.read_html(url_400)[0]['Symbol'].tolist())
    
    # 重複削除と記号変換
    return [s.replace('.', '-') for s in list(set(symbols))]

def get_data(symbol):
    try:
        # スイング用に期間を最適化
        df = yf.Ticker(symbol).history(period="1y")
        if df.empty: return None
        df = df.rename(columns={"Close": "close"})
        df["SMA50"] = df["close"].rolling(50).mean()
        df["SMA200"] = df["close"].rolling(200).mean()
        return df
    except: return None

def main():
    # 銘柄数が多いため、ランダムに50銘柄を抽出してAPI負荷を分散（重要！）
    import random
    all_symbols = get_symbols()
    target_symbols = random.sample(all_symbols, 50) 
    
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
            qty = int((balance * 0.01) / latest["close"]) # 銘柄数増に伴い1銘柄あたりの比率を調整
            try:
                api.submit_order(symbol=symbol, qty=qty, side="buy", type="market", time_in_force="day")
                messages.append(f"✅ BUY {symbol}")
            except: pass
        
        # === SELL: 損切り/デッドクロス ===
        elif symbol in positions:
            pos = api.get_position(symbol)
            if latest["close"] < float(pos.avg_entry_price) * 0.90 or (prev["SMA50"] >= prev["SMA200"] and latest["SMA50"] < latest["SMA200"]):
                api.submit_order(symbol=symbol, qty=positions[symbol], side="sell", type="market", time_in_force="day")
                messages.append(f"⚠️ SELL {symbol}")
        
        time.sleep(0.5) # APIレート制限対策

    if messages: requests.post("https://api.line.me/v2/bot/message/push", headers={"Authorization": f"Bearer {LINE_TOKEN}"}, json={"to": USER_ID, "messages": [{"type":"text","text":"\n".join(messages)}]})

if __name__ == "__main__":
    main()
