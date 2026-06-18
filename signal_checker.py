import requests
import os

# 環境変数
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")


# -----------------------------
# LINE送信（デバッグ付き）
# -----------------------------
def send_line(message):
    print("DEBUG: SENDING LINE")

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


# -----------------------------
# メイン
# -----------------------------
def main():
    print("🚀 START")

    symbol = "AAPL"

    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}"
    r = requests.get(url).json()

    print("API:", r)

    # ✅ まず強制送信（ここでLINEテスト）
    send_line("🚀 テスト送信 from BOT")

    if "Time Series (Daily)" not in r:
        send_line("❌ API失敗")
        return

    # 最新価格取得
    latest_date = list(r["Time Series (Daily)"].keys())[0]
    price = r["Time Series (Daily)"][latest_date]["4. close"]

    send_line(f"✅ AAPL価格: {price}")


if __name__ == "__main__":
    main()
