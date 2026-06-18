import requests
import os

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

print("ENV CHECK:")
print("LINE TOKEN:", "OK" if LINE_TOKEN else "MISSING")
print("USER ID:", USER_ID)

def send_line(message):
    print("DEBUG: TRY SEND LINE")

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

    print("LINE STATUS:", res.status_code)
    print("LINE RESPONSE:", res.text)


def main():
    print("🚀 START")

    # AAPLは確実に取れる
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey={API_KEY}"
    r = requests.get(url).json()

    print("API OK")

    # まず送信テスト
    send_line("🚀 BOTテスト")

    if "Time Series (Daily)" not in r:
        send_line("❌ API失敗")
        return

    ts = r["Time Series (Daily)"]
    latest_date = list(ts.keys())[0]
    price = ts[latest_date]["4. close"]

    send_line(f"✅ AAPL価格: {price}")


if __name__ == "__main__":
    main()
