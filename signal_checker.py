import yfinance as yf
import requests
import os
import pandas as pd
import time
import random
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# 設定
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

# 新SDK用クライアント
client = TradingClient(API_KEY, SECRET_KEY, paper=True)

def get_symbols():
    try:
        url_500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        url_400 = "https://en.wikipedia.org/wiki/List_of_S%26P_MidCap_400_companies"
        s500 = pd.read_html(url_500, flavor='lxml')[0]['Symbol'].tolist()
        s400 = pd.read_html(url_400, flavor='lxml')[0]['Symbol'].tolist()
        symbols = list(set([s.replace('.', '-') for s in (s500 + s400)]))
        print(f"取得した銘柄数: {
