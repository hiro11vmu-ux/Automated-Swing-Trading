import streamlit as st
import pandas as pd
import yfinance as yf
from alpaca.trading.client import TradingClient
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

        # 1. 損益サマリー（計算式でエラーを回避）
        col1, col2, col3 = st.columns(3)
        col1.metric("総資産額", f"${float(account.equity):,.2f}")
        
        # today_plを使わず、現在純資産と前日終了純資産の差分で計算
        today_pl = float(account.equity) - float(account.last_equity)
        col2.metric("本日の損益", f"${today_pl:,.2f}")
        
        col3.metric("購買力", f"${float(account.buying_power):,.2f}")

        st.markdown("---")

        # 2. ポジション情報の詳細表
        st.subheader("現在の保有銘柄")
        positions = client.get_all_positions()
        
        if positions:
            data = []
            for p in positions:
                data.append({
                    "銘柄": p.symbol,
                    "数量": p.qty,
                    "取得単価": float(p.avg_entry_price),
                    "評価額": float(p.market_value),
                    "評価損益($)": float(p.unrealized_pl)
                })
            df = pd.DataFrame(data)
            st.table(df)

            # 3. 銘柄を選択してチャートを表示
            st.subheader("チャート分析")
            selected_symbol = st.selectbox("チャートを表示する銘柄を選択してください", df["銘柄"].tolist())
            
            # yfinanceで過去1ヶ月のデータを取得
            hist = yf.Ticker(selected_symbol).history(period="1mo")
            st.line_chart(hist["Close"])
            
        else:
            st.info("現在、保有ポジションはありません。")

    except Exception as e:
        st.error(f"データの取得中にエラーが発生しました: {e}")
