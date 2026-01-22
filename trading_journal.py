import streamlit as st
import pandas as pd
import os
from datetime import datetime
import math
import io

# --- 配置页面 ---
st.set_page_config(page_title="Thorp's Edge - 交易系统", layout="wide")

# --- 数据处理 ---
# 在云端环境中，我们使用 st.session_state 来临时存储数据，防止页面刷新丢失
# 并提供上传/下载功能来持久化数据

if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=[
        "ID", "Date", "Symbol", "Type", "Direction", 
        "Entry_Price", "Stop_Loss", "Target_1", "Target_2", 
        "Quantity", "Status", "Entry_Reason", "P_L", "Notes"
    ])

def load_data_from_upload(uploaded_file):
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state.df = df
            st.success("✅ 数据加载成功！")
        except Exception as e:
            st.error(f"数据加载失败: {e}")

def get_csv_download_link(df):
    csv = df.to_csv(index=False).encode('utf-8')
    return csv

# --- 侧边栏：账户设置与数据管理 ---
st.sidebar.header("📂 数据存档 (Data Persistence)")
st.sidebar.warning("⚠️ 云端部署注意：请务必在每天结束时下载数据备份！下次使用时先上传备份文件。")

# 上传
uploaded_file = st.sidebar.file_uploader("📥 上传历史数据 (Upload CSV)", type=['csv'])
if uploaded_file is not None:
    # 避免重复加载
    if st.sidebar.button("确认加载上传的数据"):
        load_data_from_upload(uploaded_file)

# 下载
csv_data = get_csv_download_link(st.session_state.df)
st.sidebar.download_button(
    label="💾 下载当前数据备份 (Download CSV)",
    data=csv_data,
    file_name=f"trade_data_backup_{datetime.now().strftime('%Y%m%d')}.csv",
    mime='text/csv',
)

st.sidebar.markdown("---")
st.sidebar.header("💰 资金管理 (Money Management)")
capital = st.sidebar.number_input("当前总本金 (Total Capital)", value=55000.0, step=1000.0)
risk_per_trade_pct = st.sidebar.slider("单笔最大风险 % (Risk per Trade)", 0.5, 5.0, 2.0)

# --- 主界面 ---
st.title("🛡️ Thorp's Edge - 交易日记 (Cloud Ver.)")

tab1, tab2, tab3 = st.tabs(["➕ 交易计划 (Plan)", "⚡ 持仓管理 (Active)", "📊 历史复盘 (History)"])

# --- Tab 1: 交易计划计算器 ---
with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. 输入参数")
        symbol = st.text_input("标的代码 (Symbol)", value="NVDA").upper()
        trade_type = st.selectbox("类型 (Type)", ["正股 (Stock)", "期权 (Option)", "牛熊证 (CBBC)"])
        direction = st.radio("方向 (Direction)", ["做多 (Long)", "做空 (Short)"], horizontal=True)
        
        entry_price = st.number_input("入场价 (Entry Price)", value=0.0, step=0.01, format="%.3f")
        stop_loss = st.number_input("止损价 (Stop Loss)", value=0.0, step=0.01, format="%.3f")
        target_1 = st.number_input("目标价1 / 阻力位1 (Target 1)", value=0.0, step=0.01, format="%.3f")
        target_2 = st.number_input("目标价2 / 阻力位2 (Target 2)", value=0.0, step=0.01, format="%.3f")
        entry_reason = st.text_area("入场理由 (Entry Reason)", placeholder="例如：突破20日均线，群主提示阻力位在...")

    with col2:
        st.subheader("2. 风险评估 & 仓位建议")
        
        if entry_price > 0 and stop_loss > 0 and target_1 > 0:
            risk = abs(entry_price - stop_loss)
            reward = abs(target_1 - entry_price)
            
            if risk == 0:
                st.error("止损价不能等于入场价！")
            else:
                rr_ratio = reward / risk
                st.metric("单股风险", f"{risk:.3f}")
                st.metric("单股潜在盈利", f"{reward:.3f}")
                
                st.write("---")
                if rr_ratio >= 2.0:
                    st.success(f"盈亏比 **{rr_ratio:.2f} : 1** (优秀)")
                elif rr_ratio >= 1.5:
                    st.warning(f"盈亏比 **{rr_ratio:.2f} : 1** (勉强)")
                else:
                    st.error(f"盈亏比 **{rr_ratio:.2f} : 1** (索普不建议开单)")
                
                max_loss_amount = capital * (risk_per_trade_pct / 100.0)
                suggested_qty = math.floor(max_loss_amount / risk)
                
                st.info(f"建议仓位: **{suggested_qty}** 股/张 (基于 {risk_per_trade_pct}% 风险)")

                if rr_ratio >= 1.5 and suggested_qty > 0:
                    actual_qty = st.number_input("实际买入数量", value=suggested_qty, step=1)
                    if st.button("🚀 记录这笔交易"):
                        new_trade = {
                            "ID": datetime.now().strftime("%Y%m%d%H%M%S"),
                            "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Symbol": symbol,
                            "Type": trade_type,
                            "Direction": direction,
                            "Entry_Price": entry_price,
                            "Stop_Loss": stop_loss,
                            "Target_1": target_1,
                            "Target_2": target_2,
                            "Quantity": actual_qty,
                            "Status": "Open",
                            "Entry_Reason": entry_reason,
                            "P_L": 0.0,
                            "Notes": ""
                        }
                        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_trade])], ignore_index=True)
                        st.toast("交易已记录！请记得下载备份！")
                        st.balloons()

# --- Tab 2: 持仓管理 ---
with tab2:
    st.header("⚡ 当前持仓")
    # 使用 session_state 中的 df
    df = st.session_state.df
    active_trades = df[df["Status"].isin(["Open", "Half_Closed"])]
    
    if active_trades.empty:
        st.info("无活动持仓。")
    else:
        for index, row in active_trades.iterrows():
            with st.expander(f"{row['Symbol']} - {row['Status']}", expanded=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"入场: {row['Entry_Price']} | 止损: {row['Stop_Loss']}")
                with col_b:
                    st.write(f"数量: {row['Quantity']} | 方向: {row['Direction']}")
                
                c1, c2, c3 = st.columns(3)
                if row['Status'] == 'Open':
                    if c1.button("🎯 达标减半", key=f"t1_{row['ID']}"):
                        st.session_state.df.at[index, 'Status'] = 'Half_Closed'
                        st.session_state.df.at[index, 'Stop_Loss'] = row['Entry_Price']
                        st.session_state.df.at[index, 'Notes'] += "T1 Hit. "
                        st.rerun()
                
                if c3.button("💰 全部平仓", key=f"close_{row['ID']}"):
                    exit_price = st.number_input("平仓价", key=f"p_{row['ID']}")
                    if exit_price > 0:
                        st.session_state.df.at[index, 'Status'] = 'Closed'
                        # 简易计算
                        qty = row['Quantity'] if row['Status'] == 'Open' else row['Quantity'] / 2
                        pl = (exit_price - row['Entry_Price']) * qty if "Long" in row['Direction'] else (row['Entry_Price'] - exit_price) * qty
                        st.session_state.df.at[index, 'P_L'] += pl
                        st.rerun()

# --- Tab 3: 历史 ---
with tab3:
    st.header("📜 历史记录")
    st.dataframe(st.session_state.df)
