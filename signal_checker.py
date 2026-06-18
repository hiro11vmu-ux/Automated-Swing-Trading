"""
AGIX (KraneShares Public-Private AI & Technology ETF) 売買シグナル通知ツール

毎日1回実行され、以下を行う:
1. Alpha Vantage APIから日次価格データ + ファンダメンタルズを取得
2. 移動平均(SMA20/50) + RSI(14) + MACD を計算してスコア化
3. ファンダメンタルズ(PER、資金フロー方向)を補助シグナルとして加味
4. 総合判定をLINE公式アカウント(Messaging API)経由で通知

必要な環境変数 (GitHub Secretsに設定):
- ALPHA_VANTAGE_API_KEY : Alpha VantageのAPIキー
- LINE_CHANNEL_ACCESS_TOKEN : LINE公式アカウントのチャネルアクセストークン
- LINE_USER_ID : 通知を送りたい自分のLINEユーザーID
"""

import os
import sys
import time
import requests

TICKER = "AGIX"
ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"[ERROR] Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_daily_prices(api_key: str, symbol: str = TICKER) -> list[dict]:
    """Alpha VantageのTIME_SERIES_DAILYから日足の終値を取得し、古い順のリストで返す"""
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": "compact",  # 直近100日分
        "apikey": api_key,
    }
    resp = requests.get(ALPHA_VANTAGE_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "Time Series (Daily)" not in data:
        note = data.get("Note") or data.get("Information") or data
        raise RuntimeError(f"Alpha Vantage price fetch failed: {note}")

    series = data["Time Series (Daily)"]
    rows = []
    for date_str, values in series.items():
        rows.append({
            "date": date_str,
            "close": float(values["4. close"]),
        })
    rows.sort(key=lambda r: r["date"])  # 古い -> 新しい
    return rows


def fetch_overview(api_key: str, symbol: str = TICKER) -> dict:
    """OVERVIEW エンドポイントからPER等のファンダメンタルズを取得。
    AGIXのような新興ETFはフィールドが欠落/Noneのことがあるため、
    取得できない値は素直に None として扱う。
    """
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": api_key,
    }
    resp = requests.get(ALPHA_VANTAGE_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    def to_float(key):
        v = data.get(key)
        if v in (None, "None", "-", ""):
            return None
        try:
            return float(v)
        except ValueError:
            return None

    return {
        "pe_ratio": to_float("PERatio"),
        "dividend_yield": to_float("DividendYield"),
        "market_cap": to_float("MarketCapitalization"),
        "52w_high": to_float("52WeekHigh"),
        "52w_low": to_float("52WeekLow"),
    }


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------

def sma(values: list[float], period: int, i: int):
    if i < period - 1:
        return None
    window = values[i - period + 1: i + 1]
    return sum(window) / period


def ema_series(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    k = 2 / (period + 1)
    prev = None
    for i, v in enumerate(values):
        if i == period - 1:
            prev = sum(values[:period]) / period
            out[i] = prev
        elif i >= period:
            prev = v * k + prev * (1 - k)
            out[i] = prev
    return out


def rsi_series(values: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    gains = losses = 0.0
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        gain = max(diff, 0.0)
        loss = max(-diff, 0.0)
        if i <= period:
            gains += gain
            losses += loss
            if i == period:
                avg_g, avg_l = gains / period, losses / period
                out[i] = 100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l)
        else:
            gains = (gains * (period - 1) + gain) / period
            losses = (losses * (period - 1) + loss) / period
            out[i] = 100.0 if losses == 0 else 100 - 100 / (1 + gains / losses)
    return out


def macd_hist_series(values: list[float]):
    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)
    macd_line = [
        (ema12[i] - ema26[i]) if ema12[i] is not None and ema26[i] is not None else None
        for i in range(len(values))
    ]
    macd_only = [v for v in macd_line if v is not None]
    signal_raw = ema_series(macd_only, 9)
    signal_line: list[float | None] = [None] * len(values)
    p = 0
    for i, v in enumerate(macd_line):
        if v is not None:
            signal_line[i] = signal_raw[p]
            p += 1
    hist = [
        (macd_line[i] - signal_line[i])
        if macd_line[i] is not None and signal_line[i] is not None else None
        for i in range(len(values))
    ]
    return hist


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_score(closes: list[float], overview: dict) -> dict:
    i = len(closes) - 1
    sma20 = sma(closes, 20, i)
    sma50 = sma(closes, 50, i)
    rsi_vals = rsi_series(closes, 14)
    r = rsi_vals[i]
    hist = macd_hist_series(closes)
    macd_h = hist[i]
    prev_macd_h = hist[i - 1] if i > 0 else None

    ma_score = 0.0
    if sma20 is not None and sma50 is not None:
        diff_pct = (sma20 - sma50) / sma50 * 100
        ma_score = clamp(diff_pct / 2, -1, 1)

    rsi_score = 0.0
    if r is not None:
        if r <= 30:
            rsi_score = 1.0
        elif r >= 70:
            rsi_score = -1.0
        else:
            rsi_score = (50 - r) / 20

    macd_score = 0.0
    if macd_h is not None:
        macd_score = clamp(macd_h * 3, -1, 1)
        if prev_macd_h is not None:
            if prev_macd_h < 0 <= macd_h:
                macd_score = min(1.0, macd_score + 0.3)
            if prev_macd_h > 0 >= macd_h:
                macd_score = max(-1.0, macd_score - 0.3)

    # ファンダメンタルズ補助スコア: PERが既知の場合のみ軽い重みで加味
    # (AGIXのような複合ETFはPERの「適正水準」が一意に定まらないため、
    #  単独判定はしない。極端値のみセンチメントとして反映)
    fundamental_score = 0.0
    pe = overview.get("pe_ratio")
    if pe is not None:
        if pe > 60:
            fundamental_score = -0.4  # 割高警戒
        elif pe < 20:
            fundamental_score = 0.4   # 割安余地
        else:
            fundamental_score = 0.0

    technical_composite = (ma_score + rsi_score + macd_score) / 3
    # テクニカル90%、ファンダメンタルズ10%の重み付け
    final_composite = technical_composite * 0.9 + fundamental_score * 0.1
    score_100 = round((final_composite + 1) * 50)
    score_100 = int(clamp(score_100, 0, 100))

    return {
        "sma20": sma20,
        "sma50": sma50,
        "rsi": r,
        "macd_hist": macd_h,
        "ma_score": ma_score,
        "rsi_score": rsi_score,
        "macd_score": macd_score,
        "fundamental_score": fundamental_score,
        "score_100": score_100,
    }


def verdict_label(score: int) -> tuple[str, str]:
    if score >= 70:
        return "買い", "STRONG BUY"
    if score >= 58:
        return "やや買い", "LEAN BUY"
    if score > 42:
        return "中立", "NEUTRAL"
    if score > 30:
        return "やや売り", "LEAN SELL"
    return "売り", "STRONG SELL"


# ---------------------------------------------------------------------------
# LINE notification
# ---------------------------------------------------------------------------

def build_message(latest_close: float, latest_date: str, scores: dict, overview: dict) -> str:
    label, label_en = verdict_label(scores["score_100"])

    def fmt(v, suffix=""):
        return "—" if v is None else f"{v:.2f}{suffix}"

    lines = [
        f"AGIX シグナル通知 ({latest_date})",
        "",
        f"現在値: ${latest_close:.2f}",
        f"総合判定: {label} ({label_en})",
        f"スコア: {scores['score_100']} / 100",
        "",
        "--- 内訳 ---",
        f"SMA20/50: {fmt(scores['sma20'])} / {fmt(scores['sma50'])}",
        f"RSI(14): {fmt(scores['rsi'])}",
        f"MACDヒスト: {fmt(scores['macd_hist'])}",
        f"PER: {fmt(overview.get('pe_ratio'))}",
    ]
    return "\n".join(lines)


def send_line_message(channel_token: str, user_id: str, text: str) -> None:
    headers = {
        "Authorization": f"Bearer {channel_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}],
    }
    resp = requests.post(LINE_PUSH_URL, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"LINE push failed ({resp.status_code}): {resp.text}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    av_key = get_env("ALPHA_VANTAGE_API_KEY")
    line_token = get_env("LINE_CHANNEL_ACCESS_TOKEN")
    line_user_id = get_env("LINE_USER_ID")

    print(f"[INFO] Fetching daily prices for {TICKER} ...")
    prices = fetch_daily_prices(av_key)
    closes = [p["close"] for p in prices]
    latest = prices[-1]

    if len(closes) < 50:
        print(f"[WARN] Only {len(closes)} days of data available; SMA50 may be unavailable.")

    print("[INFO] Fetching fundamentals (OVERVIEW) ...")
    # Alpha Vantage無料枠はレート制限が厳しいため、間隔を空ける
    time.sleep(15)
    try:
        overview = fetch_overview(av_key)
    except Exception as e:
        print(f"[WARN] Fundamentals fetch failed, continuing without it: {e}")
        overview = {}

    print("[INFO] Computing indicator scores ...")
    scores = compute_score(closes, overview)

    message = build_message(latest["close"], latest["date"], scores, overview)
    print("[INFO] Message to send:\n" + message)

    print("[INFO] Sending LINE notification ...")
    send_line_message(line_token, line_user_id, message)
    print("[INFO] Done.")


if __name__ == "__main__":
    main()
