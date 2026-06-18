import requests
import os

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
    print(res.text)

def main():
    print("START")
    print("TOKEN:", LINE_TOKEN)
    print("USER:", USER_ID)

    if not LINE_TOKEN or not USER_ID:
        print("❌ SECRET missing")
        return

    send_line("✅ テスト成功")

if __name__ == "__main__":
    main()
