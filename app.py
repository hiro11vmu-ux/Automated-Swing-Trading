import streamlit as st
import pandas as pd
import plotly.express as px  # 円グラフ用にインポート
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetPortfolioHistoryRequest
import os

# ページ設定
st.set_page_config(page_title="Trading Dashboard", layout="wide")
st.title("📈 自動売買ボット ダッシュボード")

# APIキー取得
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY or not SECRET_KEY:
    st.error("APIキーが設定されていません。")
else:
    try:
        client = TradingClient(API_KEY, SECRET_KEY, paper=True)
        account = client.get_account()

        # 1. 損益サマリー
        equity = float(account.equity)
        last_equity = float(account.last_equity)
        today_pl = equity - last_equity
        today_pl_percent = (today_pl / last_equity * 100) if last_equity != 0 else 0

        col1, col2 = st.columns(2)
        col1.metric("総資産額", f"${equity:,.2f}")
        col2.metric("本日の損益", f"${today_pl:,.2f}", f"{today_pl_percent:+.2f}%")

        st.markdown("---")

        # ポジションデータの取得（共通）
        positions = client.get_all_positions()
        
        if positions:
            data = []
            for p in positions:
                market_value = float(p.market_value)
                cost = float(p.qty) * float(p.avg_entry_price)
                pl_percent = (float(p.unrealized_pl) / cost * 100) if cost != 0 else 0
                data.append({
                    "銘柄": p.symbol,
                    "評価額": market_value,
                    "損益率(%)": pl_percent
                })
            df = pd.DataFrame(data)

            # グラフエリアを左右に分割
            col_chart, col_table = st.columns([1, 1])

            with col_chart:
                st.subheader("ポートフォリオ構成比")
                fig = px.pie(df, values='評価額', names='銘柄', hole=0.3) # ドーナツグラフ
                st.plotly_chart(fig, use_container_width=True)

            with col_table:
                st.subheader("保有銘柄詳細")
                st.table(df[['銘柄', '評価額', '損益率(%)']].style.format({"評価額": "${:,.2f}", "損益率(%)": "{:+.2f}%"}))
        
        else:
            st.info("現在ポジションはありません。")

    except Exception as e:
        st.error(f"エラー: {e}")
