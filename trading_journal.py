import streamlit as st
import pandas as pd
import os
from datetime import datetime
import math

# --- 配置页面 ---
st.set_page_config(page_title="Thorp's Edge - 交易系统", layout="wide")

# --- 文件路径 ---
DATA_FILE = "trade_data.csv"

# --- 辅助函数：加载和保存数据 ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=[
            "ID", "Date", "Symbol", "Type", "Direction", 
            "Entry_Price", "Stop_Loss", "Target_1", "Target_2", 
            "Quantity", "Status", "Entry_Reason", "P_L", "Notes"
        ])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 侧边栏：账户设置 ---
st.sidebar.header("💰 资金管理 (Money Management)")
capital = st.sidebar.number_input("当前总本金 (Total Capital)", value=55000.0, step=1000.0)
risk_per_trade_pct = st.sidebar.slider("单笔最大风险 % (Risk per Trade)", 0.5, 5.0, 2.0)
win_rate_assumption = st.sidebar.slider("预估胜率 (Win Rate)", 0.3, 0.8, 0.4)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 索普的教诲")
st.sidebar.info(
    "1. **生存第一**：永远不要让单笔亏损超过总资金的 2%。\n"
    "2. **期望值**：只做盈亏比 > 2:1 的交易。\n"
    "3. **纪律**：到了止损位必须走，不要抱有幻想。"
)

# --- 主界面 ---
st.title("🛡️ Thorp's Edge - 交易日记")

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
            # 计算风险回报比
            risk = abs(entry_price - stop_loss)
            reward = abs(target_1 - entry_price)
            
            if risk == 0:
                st.error("止损价不能等于入场价！")
            else:
                rr_ratio = reward / risk
                
                st.metric("单股风险 (Risk)", f"{risk:.3f}")
                st.metric("单股潜在盈利 (Reward)", f"{reward:.3f}")
                
                st.write("---")
                st.write("#### ⚖️ 盈亏比 (R:R Ratio)")
                if rr_ratio >= 2.0:
                    st.success(f"**{rr_ratio:.2f} : 1** (优秀，值得交易)")
                elif rr_ratio >= 1.5:
                    st.warning(f"**{rr_ratio:.2f} : 1** (勉强，需谨慎)")
                else:
                    st.error(f"**{rr_ratio:.2f} : 1** (太低了！索普不建议开单)")
                
                st.write("---")
                st.write("#### 🛡️ 仓位建议 (Position Size)")
                
                # 计算最大允许亏损金额
                max_loss_amount = capital * (risk_per_trade_pct / 100.0)
                # 计算建议仓位
                suggested_qty = math.floor(max_loss_amount / risk)
                
                st.info(f"你的总资金: {capital}")
                st.info(f"单笔最大允许亏损 ({risk_per_trade_pct}%): **${max_loss_amount:.2f}**")
                
                if suggested_qty <= 0:
                    st.error("无法开仓：单股风险已超过你的最大允许亏损！")
                else:
                    st.success(f"🔥 索普建议最大买入数量: **{suggested_qty}** 股/张")
                    st.caption(f"总投入金额: ${suggested_qty * entry_price:.2f}")

                # 确认开仓按钮
                if rr_ratio >= 1.5 and suggested_qty > 0:
                    actual_qty = st.number_input("实际买入数量", value=suggested_qty, step=1)
                    if st.button("🚀 记录这笔交易 (Execute Trade)"):
                        df = load_data()
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
                            "Status": "Open", # Open, Half_Closed, Closed
                            "Entry_Reason": entry_reason,
                            "P_L": 0.0,
                            "Notes": ""
                        }
                        df = pd.concat([df, pd.DataFrame([new_trade])], ignore_index=True)
                        save_data(df)
                        st.toast("交易已记录！祝你好运！")
                        st.balloons()

# --- Tab 2: 持仓管理 ---
with tab2:
    st.header("⚡ 当前持仓 (Active Trades)")
    df = load_data()
    active_trades = df[df["Status"].isin(["Open", "Half_Closed"])]
    
    if active_trades.empty:
        st.info("当前没有持仓。去制定计划吧！")
    else:
        for index, row in active_trades.iterrows():
            with st.expander(f"{row['Symbol']} ({row['Type']}) - {row['Status']} - {row['Date']}", expanded=True):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.write(f"**入场价**: {row['Entry_Price']}")
                    st.write(f"**当前止损**: {row['Stop_Loss']}")
                with col_b:
                    st.write(f"**目标1**: {row['Target_1']}")
                    st.write(f"**目标2**: {row['Target_2']}")
                with col_c:
                    st.write(f"**数量**: {row['Quantity']}")
                    st.write(f"**方向**: {row['Direction']}")
                
                st.write(f"**理由**: {row['Entry_Reason']}")
                
                st.write("---")
                st.write("**操作面板:**")
                
                c1, c2, c3 = st.columns(3)
                
                # 操作 1: 达到目标 1
                if row['Status'] == 'Open':
                    if c1.button("🎯 达到目标位 1 (Hit T1)", key=f"t1_{row['ID']}"):
                        # 逻辑：平仓一半，修改状态，提醒移动止损
                        df.at[index, 'Status'] = 'Half_Closed'
                        df.at[index, 'Notes'] += f"T1 Hit. Sold 50%. Stop moved to {row['Entry_Price']}. "
                        # 移动止损到开仓价
                        df.at[index, 'Stop_Loss'] = row['Entry_Price']
                        save_data(df)
                        st.rerun()
                
                # 操作 2: 止损离场
                if c2.button("🛑 止损离场 (Stopped Out)", key=f"stop_{row['ID']}"):
                    exit_price = st.number_input("止损成交价", key=f"price_stop_{row['ID']}")
                    if exit_price > 0:
                        df.at[index, 'Status'] = 'Closed'
                        # 简单盈亏计算 (需根据做多做空调整)
                        qty = row['Quantity'] if row['Status'] == 'Open' else row['Quantity'] / 2
                        if "Long" in row['Direction']:
                            pl = (exit_price - row['Entry_Price']) * qty
                        else:
                            pl = (row['Entry_Price'] - exit_price) * qty
                        
                        df.at[index, 'P_L'] = df.at[index, 'P_L'] + pl
                        df.at[index, 'Notes'] += f"Stopped out at {exit_price}. "
                        save_data(df)
                        st.rerun()

                # 操作 3: 完全止盈/平仓
                if c3.button("💰 完全止盈/平仓 (Close All)", key=f"close_{row['ID']}"):
                    exit_price = st.number_input("平仓成交价", key=f"price_close_{row['ID']}")
                    if exit_price > 0:
                        df.at[index, 'Status'] = 'Closed'
                        # 计算盈亏
                        qty = row['Quantity'] if row['Status'] == 'Open' else row['Quantity'] / 2
                        if "Long" in row['Direction']:
                            pl = (exit_price - row['Entry_Price']) * qty
                        else:
                            pl = (row['Entry_Price'] - exit_price) * qty
                            
                        # 如果之前平了一半，要加上之前的那部分利润（这里简化处理，假设T1没记录具体价格，只记录最后这笔。
                        # *为了更精确，建议T1时也记录一笔P_L，这里暂做简化*
                        
                        df.at[index, 'P_L'] = df.at[index, 'P_L'] + pl
                        df.at[index, 'Notes'] += f"Closed all at {exit_price}. "
                        save_data(df)
                        st.rerun()
                
                if row['Status'] == 'Half_Closed':
                    st.warning(f"⚠️ **注意**：你已经减仓一半。现在的止损价应该已经是 **{row['Entry_Price']}** (保本损)！")

# --- Tab 3: 历史复盘 ---
with tab3:
    st.header("📜 历史交易 (Trade History)")
    df = load_data()
    closed_trades = df[df["Status"] == "Closed"]
    
    if not closed_trades.empty:
        st.dataframe(closed_trades)
        
        total_pl = closed_trades['P_L'].sum()
        st.metric("总盈亏 (Total P/L)", f"${total_pl:.2f}", delta=total_pl)
    else:
        st.info("暂无已平仓的交易记录。")