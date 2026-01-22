import streamlit as st
import pandas as pd
import math
from datetime import datetime
import io

# --- 页面配置 ---
st.set_page_config(page_title="Thorp's Edge - Cathy Rules", layout="wide")

# --- Cathy 的核心规则配置 (可调整) ---
MULTIPLIER_US_OPT = 100  # 美股期权 1张=100股
DEFAULT_STOP_LOSS_PCT = 20.0  # 默认20%止损

# --- 核心逻辑：费用与盈亏计算 ---
def calculate_financials(market, qty, price, stop_loss, target, lot_size=1):
    """
    计算实际投入金额、手续费、止损止盈金额
    """
    contract_multiplier = 1
    if market == "US_Option":
        contract_multiplier = 100
    elif market == "HK_CBBC":
        contract_multiplier = lot_size # 港股需要输入每手股数，或者这里假设 qty 就是股数? 
        # 通常港股报价 0.050，买入是一手 10000 股。
        # 为了防歧义，我们让用户输入“买入股数”而不是“手”。
        contract_multiplier = 1 

    # 实际投入本金 (Principal)
    # 美股期权: 1.00 * 3张 * 100 = 300元
    invested_amount = price * qty * contract_multiplier
    
    # 手续费计算
    fees = 0.0
    if market == "US_Option": 
        # 佣金 $0.65/张 + 平台费 $0.30/张 + 杂费 (最低 $1.99 + $1.00)
        # 简单估算：每张 $2.0 (保守估计)
        # 很多券商单笔最低 $2-$3
        fees = max(2.0, qty * 1.0) * 2 # 买卖双边
    elif market == "HK_CBBC":
        # 港股: 0.03% + 15 + 5
        trade_val = invested_amount
        one_way = max(3.0, trade_val * 0.0003) + 15.0 + 5.0 + (trade_val * 0.00005)
        fees = one_way * 2

    # 盈亏金额计算
    # 止损金额 (负数)
    loss_amt = (stop_loss - price) * qty * contract_multiplier - fees
    # 止盈金额 (正数)
    profit_amt = (target - price) * qty * contract_multiplier - fees
    
    return invested_amount, fees, loss_amt, profit_amt

# --- 状态管理 ---
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=[
        "ID", "Date", "Market", "Symbol", "Entry", "Qty", 
        "Stop", "Target", "Invested", "Fees", "P_L", "Status"
    ])
if 'daily_loss' not in st.session_state:
    st.session_state.daily_loss = 0.0
if 'daily_wins' not in st.session_state:
    st.session_state.daily_wins = 0.0
if 'consecutive_losses' not in st.session_state:
    st.session_state.consecutive_losses = 0

# --- 侧边栏：Cathy 的纪律面板 ---
st.sidebar.title("👮‍♀️ Cathy 的纪律室")

st.sidebar.markdown("### 1. 每日熔断阀")
daily_loss_limit = st.sidebar.number_input("日内最大亏损额 ($)", value=200.0, help="如果你今天亏了这么多，必须关电脑")
st.sidebar.metric("今日已亏损", f"${st.session_state.daily_loss:.2f}", delta=-st.session_state.daily_loss)

if st.session_state.daily_loss >= daily_loss_limit:
    st.sidebar.error("🚫 触发日内熔断！请立即停止交易！")

st.sidebar.markdown("### 2. 连跪计数器")
st.sidebar.metric("今日连续止损次数", f"{st.session_state.consecutive_losses}", help="如果连续3次，请休息")
if st.session_state.consecutive_losses >= 3:
    st.sidebar.warning("☕ 连续止损3次，请去喝杯咖啡，冷静一下。")

st.sidebar.markdown("### 3. 盈利目标")
daily_target = st.sidebar.number_input("日内盈利目标 ($)", value=200.0)
st.sidebar.metric("今日已盈利", f"${st.session_state.daily_wins:.2f}")
if st.session_state.daily_wins >= daily_target:
    st.sidebar.success("🎉 目标达成！可以下班陪家人了！")

# --- 主界面 ---
st.title("🛡️ Thorp's Edge x Cathy Rules")

st.info("💡 **原则**：盈利 = 赚得多 - 赔得少。只做盈亏比合理的事。")

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📝 交易录入")
    market = st.selectbox("市场", ["美股期权 (US Option)", "港股牛熊 (HK CBBC)"])
    symbol = st.text_input("代码", value="NVDA Call").upper()
    
    # 价格录入
    entry_price = st.number_input("现价/买入价", value=1.00, step=0.01)
    
    # 止损逻辑：默认 20%
    stop_price_default = entry_price * (1 - DEFAULT_STOP_LOSS_PCT/100.0)
    stop_loss = st.number_input(f"止损价 (默认 -{DEFAULT_STOP_LOSS_PCT}%)", value=stop_price_default, step=0.01, format="%.3f")
    
    # 止盈逻辑
    target_price = st.number_input("目标价 (止盈)", value=entry_price * 1.4, step=0.01, format="%.3f")
    
    # 数量逻辑
    if market == "US_Option":
        st.write("📦 **单位：张** (1张=100股)")
        qty = st.number_input("买入张数", min_value=1, value=1)
        lot_size = 100
    else:
        st.write("📦 **单位：股** (注意港股一手可能是10000股)")
        qty = st.number_input("买入股数", min_value=100, step=100, value=10000)
        lot_size = 1

    # 计算
    invested, fees, loss_amt, profit_amt = calculate_financials(market, qty, entry_price, stop_loss, target_price, lot_size)
    
    # 资金限制检查
    max_invest_per_trade = st.number_input("单笔最大投入限制 ($)", value=500.0)
    
    if invested > max_invest_per_trade:
        st.error(f"❌ 违规！投入金额 ${invested:.0f} 超过了你的限制 ${max_invest_per_trade}！")
    else:
        st.caption(f"✅ 实际投入: ${invested:.2f} | 预计手续费: ${fees:.2f}")

with col2:
    st.subheader("⚖️ 盈亏天平")
    
    # 核心展示卡片
    c1, c2, c3 = st.columns(3)
    c1.metric("💸 如果止损 (-20%)", f"{loss_amt:.2f}", help="包含手续费亏损")
    c2.metric("💰 如果止盈", f"+{profit_amt:.2f}", help="扣除手续费盈利")
    
    # 盈亏比
    risk = abs(loss_amt)
    reward = profit_amt
    if risk > 0:
        rr = reward / risk
        c3.metric("盈亏比 (R:R)", f"{rr:.2f}")
    
    st.write("---")
    
    # 决策区
    if risk > 0 and rr < 1.5:
        st.warning("⚠️ **不建议交易**：盈亏比低于 1.5，这笔交易不划算！")
    elif invested > max_invest_per_trade:
        st.error("🚫 **禁止交易**：仓位过重！")
    elif st.session_state.daily_loss >= daily_loss_limit:
        st.error("🚫 **禁止交易**：今日已熔断！")
    else:
        st.success("✅ **符合纪律**：可以开单")
        if st.button("🚀 执行交易 (Execute)", type="primary"):
            new_trade = {
                "ID": datetime.now().strftime("%H%M%S"),
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Market": market,
                "Symbol": symbol,
                "Entry": entry_price,
                "Qty": qty,
                "Stop": stop_loss,
                "Target": target_price,
                "Invested": invested,
                "Fees": fees,
                "P_L": 0.0, # 初始未平仓
                "Status": "Open"
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_trade])], ignore_index=True)
            st.toast("交易已记录！祝你好运！")

st.write("---")
st.subheader("⚡ 持仓与平仓")

# 持仓列表
active_trades = st.session_state.df[st.session_state.df["Status"] == "Open"]
if not active_trades.empty:
    for idx, row in active_trades.iterrows():
        with st.expander(f"{row['Symbol']} (成本 {row['Entry']})", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"投入: ${row['Invested']:.2f}")
                st.write(f"止损: {row['Stop']} (预计亏 {row['Invested'] * 0.2:.2f})")
            
            with col_b:
                # 平仓按钮
                close_price = st.number_input(f"平仓价格", key=f"cp_{row['ID']}")
                if st.button("平仓结算", key=f"btn_{row['ID']}"):
                    # 计算最终盈亏
                    multiplier = 100 if row['Market'] == "US_Option" else 1
                    gross_pl = (close_price - row['Entry']) * row['Qty'] * multiplier
                    net_pl = gross_pl - row['Fees'] # 扣除双边手续费
                    
                    # 更新数据
                    st.session_state.df.at[idx, 'Status'] = 'Closed'
                    st.session_state.df.at[idx, 'P_L'] = net_pl
                    
                    # 更新今日统计
                    if net_pl < 0:
                        st.session_state.daily_loss += abs(net_pl)
                        st.session_state.consecutive_losses += 1
                        st.error(f"止损离场。亏损 ${abs(net_pl):.2f}")
                    else:
                        st.session_state.daily_wins += net_pl
                        st.session_state.consecutive_losses = 0 # 盈利清空连跪
                        st.success(f"盈利离场！赚取 ${net_pl:.2f}")
                    
                    st.rerun()

# 历史记录
st.write("---")
st.subheader("📜 今日战绩")
st.dataframe(st.session_state.df)

# 下载
csv = st.session_state.df.to_csv(index=False).encode('utf-8')
st.download_button("💾 下载今日复盘数据", csv, "cathy_journal.csv", "text/csv")

# 上传
uploaded = st.file_uploader("📥 加载旧数据", type="csv")
if uploaded and st.button("加载"):
    st.session_state.df = pd.read_csv(uploaded)
    st.rerun()
