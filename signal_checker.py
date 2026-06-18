import yfinance as yf
import requests
import os
import pandas as pd
import random
from datetime import datetime
import alpaca_trade_api as tradeapi

# =========================
# 環境変数（安全チェック付き）
# =========================
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

# ✅ エラー防止（ここ重要）
if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    print("❌ Alpaca APIキーが設定されていません")
    exit()


# ✅ Paperトレード
api = tradeapi.REST(
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    base_url="https://paper-api.alpaca.markets"
)


# =========================
# LINE送信
# =========================
def send_line(message):
    if not LINE_TOKEN:
        print("LINEトークンなし")
        return

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


# =========================
# 銘柄取得（403対策）
# =========================
def get_symbols():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text
        table = pd.read_html(html)[0]
        return [s.replace(".", "-") for s in table["Symbol"].tolist()]
    except:
        print("⚠️ 銘柄取得失敗 → fallback")
        return ["AAPL", "MSFT", "NVDA", "AMZN"]


# =========================
# データ取得
# =========================
def get_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period="3mo")

        if df is None or df.empty:
            return None, None

        df = df.rename(columns={"Close": "close"})
        return df, stock.info

    except:
        return None, None


# =========================
# 指標
# =========================
def calc_indicators(df):
    df["SMA20"] = df["close"].rolling(20).mean()
    df["SMA50"] = df["close"].rolling(50).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()

    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()

    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    df["TR"] = (df["High"] - df["Low"]).abs()
    df["ATR"] = df["TR"].rolling(14).mean()

    return df


# =========================
# 判定
# =========================
def buy_logic(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0

    if latest["SMA20"] > latest["SMA50"]:
        score += 1
    if latest["RSI"] < 35:
        score += 1
    if prev["MACD"] <= prev["Signal"] and latest["MACD"] > latest["Signal"]:
        score += 2

    return score


def sell_logic(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    signals = []

    if latest["RSI"] > 70:
        signals.append("RSI過熱")
    if prev["MACD"] >= prev["Signal"] and latest["MACD"] < latest["Signal"]:
        signals.append("MACDデッドクロス")
    if latest["close"] < latest["SMA20"]:
        signals.append("SMA割れ")

    return signals


# =========================
# メイン
# =========================
def main():
    print("🚀 START")

    messages = []

    symbols = get_symbols()
    symbols = random.sample(symbols, min(30, len(symbols)))

    # ✅ 保有株チェック
    positions = [p.symbol for p in api.list_positions()]

    for symbol in symbols:

        df, info = get_data(symbol)

        if df is None or len(df) < 20:
            continue

        df = calc_indicators(df)

        total = buy_logic(df)
        sell_signals = sell_logic(df)

        price = df.iloc[-1]["close"]

        # =====================
        # BUY
        # =====================
        if total >= 3 and symbol not in positions:
            try:
                api.submit_order(
                    symbol=symbol,
                    qty=1,
                    side="buy",
                    type="market",
                    time_in_force="day"
                )
                print(f"✅ BUY: {symbol}")
                messages.append(f"✅ BUY {symbol} {round(price,2)}")

            except Exception as e:
                print("BUYエラー:", e)

        # =====================
        # SELL
        # =====================
        if sell_signals and symbol in positions:
            try:
                api.submit_order(
                    symbol=symbol,
                    qty=1,
                    side="sell",
                    type="market",
                    time_in_force="day"
                )
                print(f"⚠️ SELL: {symbol}")
                messages.append(f"⚠️ SELL {symbol}")

            except Exception as e:
                print("SELLエラー:", e)

    # ✅ LINE通知
    if messages:
        send_line("\n".join(messages))
    else:
        print("シグナルなし")


if __name__ == "__main__":
    main()
