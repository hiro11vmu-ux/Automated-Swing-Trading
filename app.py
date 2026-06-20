import streamlit as st
import pandas as pd
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

        # 損益サマリーの計算
        equity = float(account.equity)
        last_equity = float(account.last_equity)
        today_pl = equity - last_equity
        # 本日の損益率 (%) = (本日の損益 / 前日終了時の資産) * 100
        today_pl_percent = (today_pl / last_equity * 100) if last_equity != 0 else 0

        # 1. 損益サマリー（購買力を消して2列に）
        col1, col2 = st.columns(2)
        col1.metric("総資産額", f"${equity:,.2f}")
        col2.metric("本日の損益", f"${today_pl:,.2f}", f"{today_pl_percent:+.2f}%")

        st.markdown("---")

        # 2. ポートフォリオ推移チャート
        st.subheader("ポートフォリオ資産推移（1ヶ月）")
        history = client.get_portfolio_history(GetPortfolioHistoryRequest(period="1M"))
        df_history = pd.DataFrame({'Date': history.timestamp, 'Equity': history.equity})
        df_history.set_index('Date', inplace=True)
        st.line_chart(df_history['Equity'])

        # 3. ポジション情報（パーセント表示）
        st.subheader("現在の保有銘柄詳細")
        positions = client.get_all_positions()
        
        if positions:
            data = []
            for p in positions:
                cost = float(p.qty) * float(p.avg_entry_price)
                pl_percent = (float(p.unrealized_pl) / cost * 100) if cost != 0 else 0
                
                data.append({
                    "銘柄": p.symbol,
                    "数量": p.qty,
                    "評価損益($)": f"${float(p.unrealized_pl):,.2f}",
                    "損益率(%)": f"{pl_percent:+.2f}%"
                })
            st.table(pd.DataFrame(data))
        else:
            st.info("現在ポジションはありません。")

    except Exception as e:
        st.error(f"データの取得中にエラーが発生しました: {e}")
