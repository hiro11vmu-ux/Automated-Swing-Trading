import requests
import os

# =============================
# 環境変数
# =============================
API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

print("ENV CHECK:")
print("API KEY:", "OK" if API_KEY else "MISSING")
print("LINE TOKEN:", "OK" if LINE_TOKEN else "MISSING")
print("USER ID:", USER_ID)


# =============================
# LINE送信（絶対落ちない）
# =============================
def send_line(message):
    print("DEBUG: TRY SEND LINE")

    try:
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

    except Exception as e:
        print("LINE ERROR:", str(e))


# =============================
# MAIN
# =============================
def main():
    print("🚀 START")

    try:
        # -----------------
        # API取得
        # -----------------
        symbol = "AAPL"  # ←確実に動く銘柄

        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}"
        r = requests.get(url).json()

        print("API RESPONSE:")
        print(r)

        # -----------------
        # 強制送信テスト
        # -----------------
        send_line("🚀 BOTテスト確認①")

        # -----------------
        # データチェック
        # -----------------
        if "Time Series (Daily)" not in r:
            send_line("❌ APIデータ取得失敗")
            return

        # -----------------
        # 最新価格取得
        # -----------------
        ts = r["Time Series (Daily)"]
        latest_date = list(ts.keys())[0]
        price = ts[latest_date]["4. close"]

        print("PRICE:", price)

        # -----------------
        # 最終送信
        # -----------------
        send_line(f"✅ AAPL価格: {price}")

    except Exception as e:
        print("MAIN ERROR:", str(e))
        send_line("❌ スクリプトエラー発生")


if __name__ == "__main__":
    main()
