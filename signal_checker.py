import requests
import os

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

def send_line(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": message}]
    }

    res = requests.post(url, headers=headers, json=data)
    print("LINE RESPONSE:", res.text)

def main():
    print("🚀 START")

    symbol = "AAPL"

    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}"
    r = requests.get(url).json()

    print("API:", r)

    if "Time Series (Daily)" not in r:
        send_line("❌ API失敗")
        return

    # 価格だけ取得（シンプル）
    latest_date = list(r["Time Series (Daily)"].keys())[0]
    price = r["Time Series (Daily)"][latest_date]["4. close"]

    send_line(f"✅ AAPL価格: {price}")

if __name__ == "__main__":
    main()
