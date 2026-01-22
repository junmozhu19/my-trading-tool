import streamlit as st
import pandas as pd
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="Cathy's Discipline Trader", layout="wide")

# --- Cathy 的核心参数 (可在此调整) ---
MULTIPLIER_US_OPT = 100
DEFAULT_STOP_LOSS_PCT = 20.0  # 默认止损百分比
DAILY_LOSS_LIMIT = 2000.0     # 日内最大亏损熔断线 (美元)
CONSECUTIVE_LOSS_LIMIT = 3    # 连续止损次数限制

# --- 核心逻辑：全市场费用与盈亏计算 ---
def calculate_pre_trade(market, qty, entry, stop, target):
    """
    计算开仓前的所有关键数据：投入、手续费、止损亏损额、止盈盈利额、盈亏比
    """
    multiplier = 1
    actual_shares = qty
    
    # 1. 识别乘数
    if market == "美股期权 (US Option)":
        multiplier = 100
        actual_shares = qty * 100
    elif market == "港股牛熊 (HK CBBC)":
        multiplier = 1 # 假设直接输入股数
        actual_shares = qty
    elif market == "美股正股 (US Stock)":
        multiplier = 1
        actual_shares = qty
    elif market == "港股正股 (HK Stock)":
        multiplier = 1
        actual_shares = qty

    # 2. 资金投入
    invested = entry * actual_shares

    # 3. 手续费估算 (双边)
    fees = 0.0
    if market == "美股期权 (US Option)":
        fees = max(2.0, qty * 0.8) * 2
    elif market == "美股正股 (US Stock)":
        fees = max(2.0, actual_shares * 0.01) * 2
    elif "HK" in market:
        trade_val = invested
        one_way = max(15.0, trade_val * 0.0003 + 15.0) # 简易估算: 佣金+平台费
        fees = one_way * 2

    # 4. 盈亏推演
    # 止损时的净亏损 (含手续费)
    loss_amt = (entry - stop) * actual_shares + fees # 注意：这里 loss_amt 是正数代表亏损额
    if stop > entry: # 做空情况暂不考虑，假设做多
         loss_amt = (stop - entry) * actual_shares + fees

    # 止盈时的净盈利 (扣手续费)
    profit_amt = (target - entry) * actual_shares - fees
    
    # 盈亏比
    rr = 0.0
    if loss_amt > 0:
        rr = profit_amt / loss_amt

    return invested, fees, loss_amt, profit_amt, rr, actual_shares

# --- 初始化数据 ---
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=[
        "ID", "Date", "Market", "Symbol", "Entry", "Qty_Display", "Actual_Shares",
        "Stop_Price", "Target_Price", "Invested", "Fees", "Exit_Price", "Net_P_L", "Status"
    ])

# --- 侧边栏：Cathy 的纪律室 (实时监控) ---
st.sidebar.title("👮‍♀️ 纪律监控室")

# 1. 今日统计
today_str = datetime.now().strftime("%Y-%m-%d")
today_trades = st.session_state.df[st.session_state.df['Date'] == today_str]
today_closed = today_trades[today_trades['Status'] == 'Closed']

today_pl = today_closed['Net_P_L'].sum()
today_loss_count = len(today_closed[today_closed['Net_P_L'] < 0])

# 2. 熔断状态检查
is_melt_down = False
if today_pl < -DAILY_LOSS_LIMIT:
    is_melt_down = True
    st.sidebar.error(f"🚫 **日内熔断触发！**\n今日已亏损 ${abs(today_pl):.2f} (限额 ${DAILY_LOSS_LIMIT})")
    st.sidebar.markdown("## 🛑 停止交易！关电脑！")
elif today_loss_count >= CONSECUTIVE_LOSS_LIMIT:
    st.sidebar.warning(f"⚠️ **连续止损警告**\n今日已连跪 {today_loss_count} 次。\nCathy 建议：休息一下，不要上头。")
else:
    st.sidebar.success("✅ 状态良好，继续保持纪律。")

st.sidebar.divider()
st.sidebar.metric("今日净盈亏", f"${today_pl:.2f}")
st.sidebar.metric("今日交易笔数", len(today_trades))

# --- 主界面 ---
st.title("🛡️ 交易执行终端")

# 1. 开单区 (核心)
st.subheader("1. 制定交易计划 (Plan Your Trade)")

if is_melt_down:
    st.error("⛔ 由于触发日内亏损熔断，开仓功能已锁定。请严格遵守纪律！")
else:
    with st.container(border=True):
        col_m, col_s = st.columns([1, 1])
        market = col_m.selectbox("市场类型", ["美股期权 (US Option)", "港股牛熊 (HK CBBC)", "美股正股 (US Stock)", "港股正股 (HK Stock)"])
        symbol = col_s.text_input("标的代码", value="NVDA").upper()
        
        col1, col2, col3 = st.columns(3)
        entry_price = col1.number_input("入场价格", min_value=0.001, value=1.00, step=0.01, format="%.3f")
        
        # 数量输入：根据市场类型变化提示
        if "Option" in market:
            qty = col2.number_input("买入 **张数**", min_value=1, value=1)
            col2.caption(f"相当于 {qty*100} 股")
        else:
            qty = col2.number_input("买入 **股数**", min_value=100, step=100, value=100)
            
        # 止损止盈输入 (Cathy 核心：默认给一个建议值，但必须确认)
        suggested_stop = entry_price * (1 - DEFAULT_STOP_LOSS_PCT/100.0)
        stop_price = col3.number_input(f"止损价格 (Cathy建议 < {suggested_stop:.3f})", value=suggested_stop, step=0.01, format="%.3f")
        target_price = col3.number_input("止盈价格 (目标位)", value=entry_price * 1.5, step=0.01, format="%.3f")

        st.divider()
        
        # 实时推演计算
        invested, fees, potential_loss, potential_profit, rr, actual_shares = calculate_pre_trade(market, qty, entry_price, stop_price, target_price)
        
        # 展示推演结果
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 实际投入本金", f"${invested:.2f}")
        c2.metric("💸 触发出局亏损", f"-${potential_loss:.2f}", help="包含手续费的实际亏损")
        c3.metric("🤑 止盈预期盈利", f"+${potential_profit:.2f}", help="扣除手续费的实际落袋")
        
        rr_color = "normal"
        if rr >= 2.0: rr_color = "normal" # Streamlit metric 默认绿色不好控制，用文字辅助
        
        c4.metric("⚖️ 盈亏比 (R:R)", f"{rr:.2f}")

        # 校验逻辑
        can_trade = True
        error_msg = ""
        
        if stop_price >= entry_price:
            can_trade = False
            error_msg = "❌ 止损价必须低于入场价！"
        elif rr < 1.5:
            st.warning("⚠️ 盈亏比低于 1.5，这笔交易不太划算，建议重新寻找入场点。")
        elif potential_loss > 500: # 假设单笔最大亏损容忍度
            st.warning(f"⚠️ 风险提示：如果止损，你将亏损 ${potential_loss:.0f}，这是否超出了你的心理承受力？")

        if not can_trade:
            st.error(error_msg)
            st.button("🚫 无法下单", disabled=True)
        else:
            if st.button("🚀 确认计划并开仓", type="primary"):
                new_trade = {
                    "ID": datetime.now().strftime("%H%M%S"),
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Market": market,
                    "Symbol": symbol,
                    "Entry": entry_price,
                    "Qty_Display": qty,
                    "Actual_Shares": actual_shares,
                    "Stop_Price": stop_price,
                    "Target_Price": target_price,
                    "Invested": invested,
                    "Fees": fees,
                    "Exit_Price": 0.0,
                    "Net_P_L": 0.0,
                    "Status": "Open"
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_trade])], ignore_index=True)
                st.toast("交易已录入！请严格执行止损计划！")
                st.rerun()

# 2. 持仓管理 (Cathy 的执行)
st.subheader("2. 持仓监控 (Active Trades)")
active_trades = st.session_state.df[st.session_state.df['Status'] == 'Open']

if active_trades.empty:
    st.info("当前空仓。耐心等待猎物。")
else:
    for idx, row in active_trades.iterrows():
        with st.expander(f"🔵 {row['Symbol']} | 成本: {row['Entry']} | 止损: {row['Stop_Price']}", expanded=True):
            col_info, col_action = st.columns([2, 1])
            
            with col_info:
                st.write(f"**数量**: {row['Qty_Display']} ({row['Market']})")
                st.write(f"**止盈目标**: {row['Target_Price']}")
                st.caption(f"如果不幸止损，预计亏损: -${(row['Entry'] - row['Stop_Price']) * row['Actual_Shares'] + row['Fees']:.2f}")

            with col_action:
                st.write("#### 🛑 平仓结算")
                exit_price = st.number_input("平仓成交价", key=f"exit_{row['ID']}", value=row['Entry'])
                
                # 实时算盈亏
                gross = (exit_price - row['Entry']) * row['Actual_Shares']
                net = gross - row['Fees']
                
                btn_label = f"平仓 (盈亏: ${net:.2f})"
                btn_type = "secondary"
                if net > 0: btn_type = "primary" # 赚钱变红(primary在streamlit通常是红/黑)
                
                if st.button(btn_label, key=f"close_{row['ID']}", type=btn_type):
                    st.session_state.df.at[idx, 'Status'] = 'Closed'
                    st.session_state.df.at[idx, 'Exit_Price'] = exit_price
                    st.session_state.df.at[idx, 'Net_P_L'] = net
                    st.rerun()

# 3. 复盘数据
st.divider()
st.subheader("3. 历史复盘")
st.dataframe(st.session_state.df.sort_values(by="Date", ascending=False))

# 数据存取
c1, c2 = st.columns(2)
csv = st.session_state.df.to_csv(index=False).encode('utf-8')
c1.download_button("💾 每日必做：下载备份", csv, "journal_backup.csv", "text/csv")

uploaded = c2.file_uploader("📂 加载备份", type="csv")
if uploaded and c2.button("确认加载"):
    st.session_state.df = pd.read_csv(uploaded)
    st.rerun()
