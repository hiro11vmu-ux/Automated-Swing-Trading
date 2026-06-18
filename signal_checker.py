import requests
import os
import pandas as pd

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
    requests.post(url, headers=headers, json=data)

def get_data():
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AGIX&apikey={API_KEY}"
    r = requests.get(url).json()
    ts = r["Time Series (Daily)"]

