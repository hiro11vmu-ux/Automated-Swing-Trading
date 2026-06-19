import yfinance as yf
import requests
import os
import datetime
import alpaca_trade_api as tradeapi

# 設定
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")

def send_line(msg):
    if not LINE_TOKEN: return
    requests.post("https://api.line.me/v2/bot/message/push", headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                  json={"to": USER_ID, "messages": [{"type":"text","text":msg}]})

# 15分足でデイトレデータ取得
def get_data(symbol):
    try:
        df = yf.Ticker(symbol).history(period="5d", interval="15m")
        df = df.rename(columns={"Close": "close", "High": "high", "Low": "low", "Open": "open", "Volume": "volume"})
        df["SMA20"] = df["close"].rolling(20).mean()
        df["SMA50"] = df["close"].rolling(50).mean()
        return df
    except: return None

def main():
    symbols = ["AAPL","NVDA","MSFT"]
    # エラー回避: equityの代わりにaccount_valueまたはcashを取得
    account = api.get_account()
    balance = float(account.cash) 
    positions = {p.symbol: int(p.qty) for p in api.list_positions()}
    messages = []

    # 市場終了間際の全決済ルール (15:45)
    now = datetime.datetime.now().time()
    if now >= datetime.time(15, 45):
        for symbol in positions:
            api.close_position(symbol)
            messages.append(f"⏰ EOD EXIT {symbol}")
    
    # 既存の売買ロジックをここに続ける...
    if messages: send_line("\n".join(messages))

if __name__ == "__main__":
    main()
