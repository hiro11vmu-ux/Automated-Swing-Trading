import yfinance as yf
import requests
import os
import alpaca_trade_api as tradeapi

# 設定
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

api = tradeapi.REST(
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    base_url="https://paper-api.alpaca.markets"
)

def send_line(msg):
    if not LINE_TOKEN: return
    requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {LINE_TOKEN}"},
        json={"to": USER_ID, "messages": [{"type":"text","text":msg}]}
    )

# スイングトレード用：長期トレンドを見る設定
def get_data(symbol):
    try:
        # 過去1年間の日足を取得
        df = yf.Ticker(symbol).history(period="1y")
        if df.empty: return None
        df = df.rename(columns={"Close": "close", "High": "high", "Low": "low", "Open": "open", "Volume": "volume"})
        
        # 50日と200日の移動平均線（長期トレンド重視）
        df["SMA50"] = df["close"].rolling(50).mean()
        df["SMA200"] = df["close"].rolling(200).mean()
        df["ATR"] = (df["high"] - df["low"]).rolling(14).mean()
        return df
    except:
        return None

def main():
    symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "META", "TSLA"]
    
    # APIエラー回避：equityではなくcash属性を使用
    account = api.get_account()
    balance = float(account.cash)
    positions = {p.symbol: int(p.qty) for p in api.list_positions()}
    messages = []

    for symbol in symbols:
        df = get_data(symbol)
        if df is None: continue
        
        # 直近のデータ
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        price = latest["close"]
        atr = latest["ATR"]

        # === BUY: ゴールデンクロス (SMA50がSMA200を上抜ける) ===
        if symbol not in positions:
            if prev["SMA50"] <= prev["SMA200"] and latest["SMA50"] > latest["SMA200"]:
                qty = int((balance * 0.1) / price) # 資金の10%でエントリー
                try:
                    api.submit_order(symbol=symbol, qty
