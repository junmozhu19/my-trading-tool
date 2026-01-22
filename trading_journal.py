import streamlit as st
import pandas as pd
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="Pro Trader Journal", layout="wide")

# --- 常量 ---
MULTIPLIER_US_OPT = 100
DAILY_LOSS_LIMIT = 2000.0

# --- 辅助函数：计算单次操作盈亏 ---
def calculate_pnl(market, qty, entry_price, exit_price):
    multiplier = 100 if "Option" in market else 1
    # 港股暂时假设 1
    if "HK" in market and "CBBC" not in market: multiplier = 1 
    
    trade_val = exit_price * qty * multiplier
    
    # 手续费 (双边估算，为了简化，这里计算的是“单次卖出动作”产生的双边费用分摊)
    fees = 0.0
    if "Option" in market:
        fees = max(2.0, qty * 1.0) * 2
    elif "HK" in market:
        fees = max(30.0, trade_val * 0.0006 + 30.0) # 港股较贵
    else: # 美股正股
        fees = max(2.0, qty * 0.01) * 2

    gross_pl = (exit_price - entry_price) * qty * multiplier
    net_pl = gross_pl - fees
    return net_pl, fees

# --- 数据初始化 ---
if 'positions' not in st.session_state:
    st.session_state.positions = pd.DataFrame(columns=[
        "ID", "Date", "Market", "Symbol", "Entry_Price", "Initial_Qty", 
        "Remaining_Qty", "Stop_Price", "Target_1", "Target_2", "Entry_Reason", "Status"
    ])
if 'executions' not in st.session_state:
    st.session_state.executions = pd.DataFrame(columns=[
        "Parent_ID", "Date", "Exit_Price", "Qty", "Net_P_L", "Fees", "Reason"
    ])

# --- 侧边栏：监控与心法 ---
st.sidebar.title("🛡️ 交易员指挥部")

# 1. 纪律监控
today_str = datetime.now().strftime("%Y-%m-%d")
today_execs = st.session_state.executions[st.session_state.executions['Date'] == today_str]
today_pl = today_execs['Net_P_L'].sum() if not today_execs.empty else 0.0

st.sidebar.metric("今日已实现盈亏", f"${today_pl:.2f}")

lock_trading = False
if today_pl < -DAILY_LOSS_LIMIT:
    st.sidebar.error("🚫 触发日内熔断！停止交易！")
    lock_trading = True

st.sidebar.divider()

# 2. Cathy 的心法 (Trader's Creed)
with st.sidebar.expander("📜 Cathy 的交易铁律 (必读)", expanded=True):
    st.markdown("""
    > **"投资破产往往不是因为买错一只股票，而是不断地在错误中加码，失去控制。"**
    
    **1️⃣ 资金红线**
    *   **日内熔断**: 亏损达到 **$2000** -> 关电脑！
    *   **连跪熔断**: 连续 **3次** 止损 -> 休息！
    *   **单笔风控**: 单笔亏损绝不超过 **$500** (20%止损)。
    *   **总仓位**: 期权仓位 < 总资金 **30%**。

    **2️⃣ 止损纪律**
    *   **止损**: 坚决执行 **-20%** 止损。
    *   **不加码**: 亏损时绝不加仓摊平！
    *   **不过夜**: 期权/牛熊证绝不过夜。

    **3️⃣ 盈利目标**
    *   **知足**: 每天赚 **$1000** 就该笑了，赚 **$2000** 就该走了。
    *   **人性**: 盈利拿不住，亏损拿太多 -> 这是通病，要反着来。
    
    **"我是来股市赚钱的，不是来抢钱的。"**
    """)

# --- 主界面 ---
st.title("🛡️ 专业分批交易终端")

# 1. 开仓区
with st.expander("📝 **新建仓位 (Open Position)**", expanded=True):
    if lock_trading:
        st.error("已熔断，无法开仓。")
    else:
        c1, c2, c3, c4 = st.columns(4)
        market = c1.selectbox("市场", ["美股期权 (US Option)", "港股牛熊 (HK CBBC)", "美股正股 (US Stock)", "港股正股 (HK Stock)"])
        symbol = c2.text_input("代码", value="NVDA").upper()
        entry_price = c3.number_input("开仓均价", min_value=0.01, value=1.00)
        
        qty_label = "张数" if "Option" in market else "股数"
        min_q = 1 if "Option" in market else 100
        qty = c4.number_input(f"买入{qty_label}", min_value=min_q, value=min_q)

        st.caption("计划设置 (Plan)")
        pc1, pc2, pc3 = st.columns(3)
        stop_p = pc1.number_input("止损价", value=entry_price*0.8)
        tgt1 = pc2.number_input("目标1 (减仓50%)", value=entry_price*1.2)
        tgt2 = pc3.number_input("目标2 (清仓)", value=entry_price*1.5)
        
        # 新增：入场理由 (必填)
        entry_reason = st.text_area("🤔 入场理由 (必填：为什么这笔单子值得做？)", placeholder="例如：突破日线阻力位，成交量放大，且大盘趋势向上...")

        # 检查逻辑
        valid_trade = True
        if stop_p >= entry_price:
            st.warning("⚠️ 止损必须低于开仓价")
            valid_trade = False
        if len(entry_reason) < 5:
            st.warning("⚠️ 请填写充分的入场理由！")
            valid_trade = False
        
        if valid_trade and st.button("🚀 开仓 (Execute)", type="primary"):
            new_pos = {
                "ID": datetime.now().strftime("%H%M%S"),
                "Date": today_str,
                "Market": market,
                "Symbol": symbol,
                "Entry_Price": entry_price,
                "Initial_Qty": qty,
                "Remaining_Qty": qty, 
                "Stop_Price": stop_p,
                "Target_1": tgt1,
                "Target_2": tgt2,
                "Entry_Reason": entry_reason,
                "Status": "Open"
            }
            st.session_state.positions = pd.concat([st.session_state.positions, pd.DataFrame([new_pos])], ignore_index=True)
            st.toast("开仓成功！")
            st.rerun()

# 2. 持仓管理
st.subheader("⚡ 持仓管理 (Active Positions)")

active_pos = st.session_state.positions[st.session_state.positions['Status'] == 'Open']

if active_pos.empty:
    st.info("当前无持仓。")
else:
    for idx, row in active_pos.iterrows():
        with st.container(border=True):
            # 标题栏
            title_col, info_col = st.columns([1, 3])
            title_col.markdown(f"### {row['Symbol']}")
            title_col.caption(f"ID: {row['ID']}")
            
            info_col.markdown(f"""
            **理由**: *{row['Entry_Reason']}*  
            **成本**: {row['Entry_Price']} | **剩余**: `{row['Remaining_Qty']}` / {row['Initial_Qty']}  
            🔴 **止损**: {row['Stop_Price']} | 🟢 **目标1**: {row['Target_1']}
            """)

            st.divider()
            
            # 分批平仓操作区
            c_price, c_qty, c_btn = st.columns([1, 1, 1])
            
            exit_price = c_price.number_input(f"卖出价格", key=f"p_{row['ID']}", value=row['Entry_Price'])
            
            default_sell = row['Remaining_Qty']
            if row['Remaining_Qty'] > 1:
                default_sell = int(row['Remaining_Qty'] / 2)
                
            sell_qty = c_qty.number_input(f"卖出数量", key=f"q_{row['ID']}", 
                                          min_value=1, max_value=int(row['Remaining_Qty']), 
                                          value=default_sell)

            est_pl, _ = calculate_pnl(row['Market'], sell_qty, row['Entry_Price'], exit_price)
            btn_text = f"卖出 {sell_qty} (盈亏: ${est_pl:.1f})"
            btn_color = "primary" if est_pl > 0 else "secondary"

            if c_btn.button(btn_text, key=f"btn_{row['ID']}", type=btn_color):
                new_exec = {
                    "Parent_ID": row['ID'],
                    "Date": today_str,
                    "Exit_Price": exit_price,
                    "Qty": sell_qty,
                    "Net_P_L": est_pl,
                    "Fees": 0, 
                    "Reason": "Manual"
                }
                st.session_state.executions = pd.concat([st.session_state.executions, pd.DataFrame([new_exec])], ignore_index=True)
                
                new_rem = row['Remaining_Qty'] - sell_qty
                st.session_state.positions.at[idx, 'Remaining_Qty'] = new_rem
                
                if new_rem == 0:
                    st.session_state.positions.at[idx, 'Status'] = 'Closed'
                    st.toast(f"仓位 {row['Symbol']} 已全部平仓！")
                else:
                    st.toast(f"部分减仓成功！剩余 {new_rem}")
                
                st.rerun()

# 3. 不过夜检查
st.subheader("🌙 收盘检查 (Night Watch)")
if st.button("检查违规单"):
    overnight_risks = []
    for idx, row in active_pos.iterrows():
        if "Option" in row['Market'] or "CBBC" in row['Market']:
            overnight_risks.append(f"{row['Symbol']} ({row['Remaining_Qty']} 张/股)")
    
    if overnight_risks:
        st.error(f"❌ **严重违规！以下头寸禁止过夜，请立即平仓：**\n" + "\n".join(overnight_risks))
    else:
        st.success("✅ 目前没有高风险过夜头寸。")

# 4. 历史明细
st.divider()
st.subheader("📜 执行明细 (Executions)")
st.dataframe(st.session_state.executions.sort_values(by="Date", ascending=False))

# 保存
c1, c2 = st.columns(2)
csv_exec = st.session_state.executions.to_csv(index=False).encode('utf-8')
c1.download_button("💾 下载交易流水", csv_exec, "executions.csv", "text/csv")

uploaded = c2.file_uploader("📂 加载备份 (Executions)", type="csv")
if uploaded and c2.button("加载"):
    st.session_state.executions = pd.read_csv(uploaded)
    st.rerun()
