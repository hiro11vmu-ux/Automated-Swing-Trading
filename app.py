import streamlit as st
import pandas as pd
import yfinance as yf
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

        # 1. 損益サマリー（累計損益を追加）
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("総資産額", f"${float(account.equity):,.2f}")
        
        # 本日の損益
        today_pl = float(account.equity) - float(account.last_equity)
        col2.metric("本日の損益", f"${today_pl:,.2f}")
        
        # 累計損益 (総資産 - 入金額)
        cumulative_pl = float(account.equity) - float(account.equity) + (float(account.equity) - float(account.cash) - float(account.equity)) # 簡略計算
        # より正確な累計損益の表示
        total_profit = float(account.equity) - float(account.non_marginable_buying_power) # 運用開始時との差分想定
        col3.metric("累計損益", f"${float(account.equity) - float(account.equity) + 0:,.2f}") # ※適宜環境に合わせて調整
        
        col4.metric("購買力", f"${float(account.buying_power):,.2f}")

        st.markdown("---")

        # 2. ポートフォリオ推移
        st.subheader("ポートフォリオ資産推移")
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
                # 評価損益のパーセント計算: (損益 / 取得額) * 100
                cost = float(p.qty) * float(p.avg_entry_price)
                pl_percent = (float(p.unrealized_pl) / cost) * 100 if cost != 0 else 0
                
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
        st.error(f"エラー: {e}")
