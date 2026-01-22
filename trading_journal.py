import streamlit as st
import pandas as pd
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="Thorp x Cathy 交易系统", layout="wide")

# --- 常量定义 ---
MULTIPLIER_US_OPT = 100  # 美股期权合约乘数

# --- 核心函数：费用与盈亏 ---
def calculate_trade_details(market, qty, entry_price, close_price=None):
    """
    计算单笔交易的细节：投入本金、手续费、(可选)最终盈亏
    """
    # 1. 确定合约乘数和实际股数
    multiplier = 1
    actual_shares = qty
    
    if market == "美股期权 (US Option)":
        multiplier = MULTIPLIER_US_OPT
        actual_shares = qty * multiplier # 输入2张 -> 实际200股
    elif market == "港股牛熊 (HK CBBC)":
        multiplier = 1
        actual_shares = qty # 输入10000股 -> 实际10000股

    # 2. 资金计算
    invested_principal = entry_price * actual_shares
    
    # 3. 手续费计算 (双边估算)
    fees = 0.0
    if market == "美股期权 (US Option)":
        # 估算：每张 $2.0 (含佣金+平台费+监管费)
        one_way_fee = max(2.0, qty * 0.8) 
        fees = one_way_fee * 2 # 买+卖
    elif market == "港股牛熊 (HK CBBC)":
        # 港股: 0.03% + 15 + 5
        one_way_fee = max(20.0, invested_principal * 0.0003 + 20.0)
        fees = one_way_fee * 2

    # 4. 盈亏计算 (如果有平仓价)
    net_pl = 0.0
    if close_price is not None:
        gross_pl = (close_price - entry_price) * actual_shares
        net_pl = gross_pl - fees

    return invested_principal, fees, net_pl, actual_shares

# --- 初始化数据 ---
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=[
        "ID", "Date", "Market", "Symbol", "Entry", "Qty_Display", "Actual_Shares",
        "Stop_Price", "Target_Price", "Invested", "Fees", "Exit_Price", "Net_P_L", "Status"
    ])

# --- 侧边栏：今日统计 ---
st.sidebar.title("📊 今日战况")
today_df = st.session_state.df[st.session_state.df['Date'] == datetime.now().strftime("%Y-%m-%d")]
today_pl = today_df['Net_P_L'].sum()

if today_pl >= 0:
    st.sidebar.metric("今日净盈亏", f"+${today_pl:.2f}", delta="盈利中")
else:
    st.sidebar.metric("今日净盈亏", f"-${abs(today_pl):.2f}", delta="亏损中", delta_color="inverse")

# 止损计数
loss_count = len(today_df[today_df['Net_P_L'] < 0])
st.sidebar.write(f"今日止损次数: **{loss_count}**")
if loss_count >= 3:
    st.sidebar.error("⚠️ 连续止损报警：请停止交易！")

# --- 主界面 ---
st.title("🛡️ 实战交易台")

# 1. 开单区
with st.expander("📝 **新建交易 (Open Trade)**", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    market = c1.selectbox("市场", ["美股期权 (US Option)", "港股牛熊 (HK CBBC)"])
    symbol = c2.text_input("代码", value="NVDA Call").upper()
    entry_price = c3.number_input("买入单价", min_value=0.01, value=1.00, step=0.01)
    
    # 数量输入逻辑优化
    if "Option" in market:
        qty_input = c4.number_input("买入 **张数** (手)", min_value=1, value=1)
        c4.caption(f"实际对应 {qty_input * 100} 股")
    else:
        qty_input = c4.number_input("买入 **股数**", min_value=100, step=100, value=10000)
    
    # 预计算
    invested, fees, _, _ = calculate_trade_details(market, qty_input, entry_price)
    
    st.info(f"💰 本金投入: **${invested:.2f}** | 预计双边手续费: **${fees:.2f}**")
    
    if st.button("🚀 下单开仓", type="primary"):
        new_trade = {
            "ID": datetime.now().strftime("%H%M%S"),
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Market": market,
            "Symbol": symbol,
            "Entry": entry_price,
            "Qty_Display": qty_input, # 显示用的数量 (张)
            "Actual_Shares": qty_input * 100 if "Option" in market else qty_input, # 计算用的数量
            "Stop_Price": 0.0, # 后续设置
            "Target_Price": 0.0,
            "Invested": invested,
            "Fees": fees,
            "Exit_Price": 0.0,
            "Net_P_L": 0.0,
            "Status": "Open"
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_trade])], ignore_index=True)
        st.rerun()

# 2. 持仓管理区 (核心)
st.subheader("⚡ 持仓管理 (Active Positions)")
active_trades = st.session_state.df[st.session_state.df['Status'] == 'Open']

if active_trades.empty:
    st.write("暂无持仓。")
else:
    for idx, row in active_trades.iterrows():
        # 每一行持仓是一个卡片
        with st.container():
            st.markdown(f"### {row['Symbol']} | 成本: {row['Entry']} | 持仓: {row['Qty_Display']} {'张' if 'Option' in row['Market'] else '股'}")
            
            col_input, col_calc, col_btn = st.columns([2, 2, 1])
            
            with col_input:
                exit_price = st.number_input(f"平仓价格 ({row['ID']})", min_value=0.01, value=row['Entry'], step=0.01, key=f"price_{row['ID']}")
            
            with col_calc:
                # 实时计算盈亏
                gross = (exit_price - row['Entry']) * row['Actual_Shares']
                net = gross - row['Fees']
                
                if net > 0:
                    st.success(f"预计盈利: +${net:.2f}")
                elif net < 0:
                    st.error(f"预计亏损: -${abs(net):.2f}")
                else:
                    st.warning("预计保本")

            with col_btn:
                if st.button("确认平仓", key=f"close_{row['ID']}"):
                    st.session_state.df.at[idx, 'Status'] = 'Closed'
                    st.session_state.df.at[idx, 'Exit_Price'] = exit_price
                    st.session_state.df.at[idx, 'Net_P_L'] = net
                    st.toast(f"平仓成功！净盈亏: ${net:.2f}")
                    st.rerun()
            st.divider()

# 3. 历史记录区
st.subheader("📜 交易日志")
st.dataframe(st.session_state.df[['Date', 'Symbol', 'Market', 'Qty_Display', 'Entry', 'Exit_Price', 'Net_P_L', 'Status']])

# 下载功能
csv = st.session_state.df.to_csv(index=False).encode('utf-8')
st.download_button("💾 保存数据", csv, "my_trades.csv", "text/csv")

# 上传功能
uploaded = st.file_uploader("📥 加载旧数据", type="csv")
if uploaded and st.button("加载"):
    st.session_state.df = pd.read_csv(uploaded)
    st.rerun()
