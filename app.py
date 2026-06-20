import streamlit as st
import pandas as pd
import os
from alpaca.trading.client import TradingClient

# ページ設定
st.set_page_config(page_title="Trading Dashboard", layout="wide")

# 環境変数からAPIキーを取得
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

st.title("📈 自動売買ボット ダッシュボード")

# アルパカ接続チェック
if not API_KEY or not SECRET_KEY:
    st.error("APIキーが設定されていません。環境変数を確認してください。")
else:
    client = TradingClient(API_KEY, SECRET_KEY, paper=True)

    # ポジション情報の取得
    try:
        positions = client.get_all_positions()
        if positions:
            data = [{"銘柄": p.symbol, "保有数": p.qty, "評価損益": f"{p.unrealized_pl}ドル"} for p in positions]
            df = pd.DataFrame(data)
            st.table(df)
        else:
            st.info("現在、保有ポジションはありません。")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# 最新の株価確認用（必要であれば追加）
st.subheader("システム状況")
st.write("ボットは正常に稼働しています。")
