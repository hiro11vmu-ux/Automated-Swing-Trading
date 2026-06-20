import streamlit as st
import pandas as pd
import plotly.express as px
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
    st.error("APIキーが設定されていません。StreamlitのSecretsを確認してください。")
else:
    try:
        client = TradingClient(API_KEY, SECRET_KEY, paper=True)
        account = client.get_account()

        # 1. 損益サマリー（本日の損益％ ＆ 累計損益）
        equity = float(account.equity)
        last_equity = float(account.last_equity)
        today_pl = equity - last_equity
        today_pl_percent = (today_pl / last_equity * 100) if last_equity != 0 else 0
        
        # 累計損益（現資産 - 初期元本$100,000と仮定）
        cumulative_pl = equity - 100000.0

        col1, col2, col3 = st.columns(3)
        col1.metric("総資産額", f"${equity:,.2f}")
        col2.metric("本日の損益", f"${today_pl:,.2f}", f"{today_pl_percent:+.2f}%")
        col3.metric("累計損益(概算)", f"${cumulative_pl:,.2f}")

        st.markdown("---")

        # 2. ポートフォリオ推移チャート（日付軸修正済み）
        st.subheader("ポートフォリオ資産推移（1ヶ月）")
        history = client.get_portfolio_history(GetPortfolioHistoryRequest(period="1M"))
        df_history = pd.DataFrame({'Date': pd.to_datetime(history.timestamp, unit='s'), 'Equity': history.equity})
        df_history.set_index('Date', inplace=True)
        st.line_chart(df_history['Equity'])

        # 3. 円グラフと詳細表
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

            col_chart, col_table = st.columns([1, 1])
            with col_chart:
                st.subheader("ポートフォリオ構成比")
                fig = px.pie(df, values='評価額', names='銘柄', hole=0.3)
                st.plotly_chart(fig, use_container_width=True)

            with col_table:
                st.subheader("保有銘柄詳細")
                st.table(df.style.format({"評価額": "${:,.2f}", "損益率(%)": "{:+.2f}%"}))
        else:
            st.info("現在ポジションはありません。")

    except Exception as e:
        st.error(f"データの取得中にエラーが発生しました: {e}")
