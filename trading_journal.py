import streamlit as st
import pandas as pd
import math
from datetime import datetime
import io

# --- 页面配置 ---
st.set_page_config(page_title="Thorp's Edge - 实战版", layout="wide", initial_sidebar_state="expanded")

# --- 核心逻辑：手续费计算器 ---
def calculate_fees(market, qty, price, order_amount=0):
    """
    计算富途牛牛估算手续费 (双向：买+卖)
    """
    fees = 0.0
    if market == "US_Option": # 美股期权
        # 佣金: $0.65/张, 最低 $1.99
        commission = max(1.99, qty * 0.65)
        # 平台费: $0.30/张, 最低 $1.00 (假设套餐)
        platform = max(1.00, qty * 0.30)
        # 监管费等杂费 (预估 $0.05/张)
        other = qty * 0.05
        # 单边总计
        one_way = commission + platform + other
        fees = one_way * 2 # 买入+卖出
        
    elif market == "HK_CBBC": # 港股牛熊证
        # 佣金: 0.03% * 交易额, 最低 HK$3.00
        commission = max(3.00, order_amount * 0.0003)
        # 平台费: HK$15.00/笔
        platform = 15.00
        # 交易征费等 (约 0.00565%)
        other = order_amount * 0.0000565 + 5.0 # +5块结算费
        # 单边
        one_way = commission + platform + other
        fees = one_way * 2
        
    elif market == "US_Stock": # 美股正股
        # 简易估算: $0.0049/股, 最低 $0.99
        commission = max(0.99, qty * 0.0049)
        platform = max(1.00, qty * 0.005)
        fees = (commission + platform) * 2

    return round(fees, 2)

# --- 数据状态 ---
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=[
        "ID", "Date", "Market", "Symbol", "Direction", 
        "Entry_Price", "Quantity", "Stop_Loss", "Target", 
        "Fees_Est", "Status", "P_L", "Notes"
    ])

# --- 侧边栏：资金池 ---
st.sidebar.header("💰 我的小金库")
capital_option = st.sidebar.number_input("美股期权本金 ($)", value=700.0, help="约5000人民币")
capital_cbbc = st.sidebar.number_input("港股牛熊本金 (HK$)", value=5500.0, help="约5000人民币")
capital_stock = st.sidebar.number_input("正股本金 (¥/HK/$)", value=30000.0)

# --- 主界面 ---
st.title("🛡️ Thorp's Edge - 交易模拟台")

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("1. 选筹与定价")
    market_type = st.selectbox("我要玩什么？", ["美股期权 (US Option)", "港股牛熊 (HK CBBC)", "正股 (Stock)"])
    
    symbol = st.text_input("代码 (如 NVDA 240202 Call)", value="NVDA Call").upper()
    direction = st.radio("方向", ["做多 (Long)", "做空 (Short)"], horizontal=True)
    
    # 价格输入
    st.info("👇 请输入 **期权/牛熊证** 的实际价格，不是正股价格！")
    entry_price = st.number_input("现价/买入价", value=0.0, step=0.01, format="%.3f")
    
    # 数量选择
    if "Option" in market_type:
        max_qty = 10 # 期权限制
        st.write("🛑 **新手保护**：期权每次建议不超过 3 张")
    else:
        max_qty = 10000
        
    qty = st.number_input("买入数量 (张/股)", min_value=1, max_value=max_qty, value=1)

    # 资金检查
    total_cost = entry_price * qty
    fees = 0.0
    
    if "Option" in market_type:
        fees = calculate_fees("US_Option", qty, entry_price)
        st.caption(f"预计总手续费 (买+卖): ${fees}")
        if total_cost + fees/2 > capital_option:
            st.error(f"❌ 钱不够！需要 ${total_cost + fees/2:.2f}，你只有 ${capital_option}")
    elif "CBBC" in market_type:
        fees = calculate_fees("HK_CBBC", qty, entry_price, total_cost)
        st.caption(f"预计总手续费 (买+卖): HK${fees}")
        if total_cost + fees/2 > capital_cbbc:
            st.error(f"❌ 钱不够！需要 HK${total_cost + fees/2:.2f}，你只有 HK${capital_cbbc}")

with col2:
    st.subheader("2. 盈亏模拟器 (所见即所得)")
    
    if entry_price > 0:
        # 止损止盈设置
        stop_loss = st.number_input("止损价 (打到这必须跑)", value=entry_price * 0.9, format="%.3f")
        target_price = st.number_input("目标价 (止盈)", value=entry_price * 1.2, format="%.3f")
        
        # 模拟计算
        potential_loss = (abs(entry_price - stop_loss) * qty) + fees
        potential_profit = (abs(target_price - entry_price) * qty) - fees
        
        # 展示卡片
        c1, c2 = st.columns(2)
        c1.metric("😭 如果止损 (含手续费)", f"-{potential_loss:.2f}", delta_color="inverse")
        c2.metric("🤑 如果止盈 (扣手续费)", f"+{potential_profit:.2f}")
        
        # 盈亏比计算
        if potential_loss > 0:
            rr = potential_profit / potential_loss
            if rr > 2:
                st.success(f"✅ 盈亏比 {rr:.2f} : 1 (值得博！)")
            else:
                st.warning(f"⚠️ 盈亏比 {rr:.2f} : 1 (不太划算，手续费吃太多了)")
        
        # 动态滑块
        st.write("---")
        st.write("🎚️ **拖动滑块，看看价格变动对钱包的影响：**")
        sim_change = st.slider("价格变化 %", -50, 100, 0)
        sim_price = entry_price * (1 + sim_change / 100.0)
        
        if "Long" in direction:
            gross_pl = (sim_price - entry_price) * qty
        else:
            gross_pl = (entry_price - sim_price) * qty
            
        net_pl = gross_pl - fees # 扣除双边手续费
        
        st.write(f"价格变为: **{sim_price:.3f}**")
        if net_pl > 0:
            st.markdown(f"### 🎉 净赚: **+{net_pl:.2f}**")
        else:
            st.markdown(f"### 💸 净亏: **{net_pl:.2f}**")
            
        # 记录按钮
        if st.button("📝 既然算好了，就记下来！", type="primary"):
            new_trade = {
                "ID": datetime.now().strftime("%H%M%S"),
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Market": market_type,
                "Symbol": symbol,
                "Direction": direction,
                "Entry_Price": entry_price,
                "Quantity": qty,
                "Stop_Loss": stop_loss,
                "Target": target_price,
                "Fees_Est": fees,
                "Status": "Open",
                "P_L": 0.0,
                "Notes": ""
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_trade])], ignore_index=True)
            st.toast("已保存到下方表格")

st.markdown("---")
st.subheader("📋 交易记录本")

# 显示记录
st.dataframe(st.session_state.df)

# 数据下载区
csv = st.session_state.df.to_csv(index=False).encode('utf-8')
st.download_button(
    "💾 下载备份 (记得每天点一下)",
    csv,
    "my_trading_journal.csv",
    "text/csv",
    key='download-csv'
)

# 上传区
uploaded = st.file_uploader("📥 上传旧数据", type="csv")
if uploaded:
    if st.button("加载数据"):
        st.session_state.df = pd.read_csv(uploaded)
        st.rerun()
