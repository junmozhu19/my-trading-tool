import streamlit as st
import pandas as pd
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="Pro Trader Journal", layout="wide", page_icon="📈")

# --- 自定义 CSS 样式 (UI 核心) ---
st.markdown("""
<style>
    /* 全局字体优化 - 统一使用无衬线字体，解决格式混乱问题 */
    .stApp {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 侧边栏卡片样式 */
    .sidebar-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 5px solid #ff4b4b; /* 默认红色边框 */
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .sidebar-card h4 {
        margin-top: 0;
        margin-bottom: 8px;
        color: #333;
        font-size: 15px;
        font-weight: 700;
    }
    .sidebar-card ul {
        padding-left: 18px; 
        margin-bottom: 0;
    }
    .sidebar-card li {
        font-size: 14px;
        color: #444;
        margin-bottom: 4px;
        line-height: 1.5;
    }
    /* 高亮文字样式 */
    .highlight-red { color: #d9534f; font-weight: bold; }
    .highlight-green { color: #2e7d32; font-weight: bold; }
    .highlight-orange { color: #e67e22; font-weight: bold; }
    
    /* 主界面：持仓卡片样式 */
    .trade-card {
        border: 1px solid #e0e0e0;
        padding: 18px;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 2px; /* Streamlit 容器间距 */
    }
    .trade-header {
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 12px;
        border-bottom: 1px solid #f0f0f0;
        padding-bottom: 8px;
    }
    .trade-symbol {
        font-size: 1.4em; 
        font-weight: 800; 
        color: #0068c9;
    }
    .trade-tag {
        background-color: #eef4ff; 
        color: #0068c9;
        padding: 3px 8px; 
        border-radius: 4px; 
        font-size: 0.75em; 
        margin-left: 8px;
        vertical-align: middle;
        font-weight: 600;
    }
    .trade-reason {
        background-color: #f8f9fa; 
        padding: 10px; 
        border-radius: 6px; 
        font-size: 0.9em; 
        color: #555;
        font-style: italic;
        margin-bottom: 15px;
        border-left: 3px solid #ccc;
    }
    .trade-stats {
        display: flex; 
        justify-content: space-between; 
        font-size: 0.95em;
        background-color: #fff;
    }
    .stat-item {
        display: flex;
        flex-direction: column;
    }
    .stat-label { font-size: 0.8em; color: #888; }
    .stat-val { font-weight: 600; }
    
</style>
""", unsafe_allow_html=True)

# --- 常量 ---
MULTIPLIER_US_OPT = 100
DAILY_LOSS_LIMIT = 2000.0

# --- 辅助函数：计算单次操作盈亏 ---
def calculate_pnl(market, qty, entry_price, exit_price):
    multiplier = 100 if "Option" in market else 1
    if "HK" in market and "CBBC" not in market: multiplier = 1 
    
    trade_val = exit_price * qty * multiplier
    
    # 手续费估算
    fees = 0.0
    if "Option" in market:
        fees = max(2.0, qty * 1.0) * 2
    elif "HK" in market:
        fees = max(30.0, trade_val * 0.0006 + 30.0)
    else: 
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

pl_color = "#d9534f" if today_pl < 0 else "#2e7d32"
st.sidebar.markdown(f"""
    <div style="padding:15px; border-radius:8px; background-color: white; text-align: center; border: 1px solid #ddd; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px;">
        <h4 style="margin:0 0 5px 0; color:#666; font-size: 14px;">今日已实现盈亏</h4>
        <h1 style="margin:0; color:{pl_color}; font-size: 28px;">${today_pl:,.2f}</h1>
    </div>
""", unsafe_allow_html=True)

lock_trading = False
if today_pl < -DAILY_LOSS_LIMIT:
    st.sidebar.error(f"🚫 触发熔断！今日亏损已超 ${DAILY_LOSS_LIMIT}")
    lock_trading = True

st.sidebar.divider()

# 2. Cathy 的心法 (UI 优化版)
st.sidebar.subheader("📜 交易铁律 (Trader's Creed)")

def creed_card(title, items, color="#ff4b4b"):
    content = ""
    for item in items:
        content += f"<li>{item}</li>"
    
    st.sidebar.markdown(f"""
    <div class="sidebar-card" style="border-left-color: {color};">
        <h4>{title}</h4>
        <ul>{content}</ul>
    </div>
    """, unsafe_allow_html=True)

creed_card("1️⃣ 资金红线 (Risk)", [
    f"日内熔断：亏损 <span class='highlight-red'>${int(DAILY_LOSS_LIMIT)}</span> -> 关电脑！",
    "连跪熔断：连续 <span class='highlight-red'>3次</span> 止损 -> 休息！",
    "单笔风控：亏损不超过 <span class='highlight-red'>$500</span> (20%)",
    "总仓位：期权 < 总资金 <span class='highlight-red'>30%</span>"
], color="#d9534f")

creed_card("2️⃣ 止损纪律 (Discipline)", [
    "坚决执行 <span class='highlight-orange'>-20%</span> 止损",
    "亏损时 <span class='highlight-red'>绝不加码</span>",
    "期权/牛熊 <span class='highlight-red'>绝不过夜</span>"
], color="#e67e22")

creed_card("3️⃣ 盈利目标 (Goals)", [
    "知足：赚 <span class='highlight-green'>$1000</span> 笑，赚 <span class='highlight-green'>$2000</span> 跑",
    "反人性：盈利要拿住，亏损要砍快",
    "<i>“我是来股市赚钱的，不是来抢钱的。”</i>"
], color="#2e7d32")

# --- 主界面 ---
st.markdown("## 📈 专业分批交易终端 <span style='font-size:0.6em; color:gray; font-weight:normal'>Professional Trading Journal</span>", unsafe_allow_html=True)

# 1. 开仓区
with st.expander("📝 **新建仓位 (Open Position)**", expanded=True):
    if lock_trading:
        st.error("🛑 已触发日内熔断，禁止开仓！请立即休息！")
    else:
        # 第一行：基础信息
        c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
        market = c1.selectbox("市场类型", ["美股期权 (US Option)", "港股牛熊 (HK CBBC)", "美股正股 (US Stock)", "港股正股 (HK Stock)"])
        symbol = c2.text_input("代码 (Symbol)", value="NVDA").upper()
        entry_price = c3.number_input("入场均价 ($)", min_value=0.01, value=1.00, step=0.01)
        
        qty_label = "张数" if "Option" in market else "股数"
        min_q = 1 if "Option" in market else 100
        qty = c4.number_input(f"买入{qty_label}", min_value=min_q, value=min_q)

        # 第二行：计划风控
        st.markdown("##### 🎯 交易计划 (Trading Plan)")
        pc1, pc2, pc3 = st.columns(3)
        stop_p = pc1.number_input("🔴 止损价 (Stop Loss)", value=round(entry_price*0.8, 2), step=0.01)
        tgt1 = pc2.number_input("🟢 目标1 (Target 50%)", value=round(entry_price*1.2, 2), step=0.01)
        tgt2 = pc3.number_input("🟢 目标2 (Target 100%)", value=round(entry_price*1.5, 2), step=0.01)
        
        # 第三行：入场理由
        entry_reason = st.text_area("🤔 入场理由 (灵魂拷问：为什么这笔单子值得做？)", 
                                  placeholder="必填。例如：回踩 20 日均线企稳，MACD 金叉，且大盘情绪配合...",
                                  height=68)

        # 提交区
        col_submit, col_check = st.columns([1, 4])
        
        valid_trade = True
        error_msgs = []
        if stop_p >= entry_price:
            error_msgs.append("⚠️ 止损价必须低于入场价")
            valid_trade = False
        if len(entry_reason.strip()) < 5:
            error_msgs.append("⚠️ 必须填写充分的入场理由")
            valid_trade = False
            
        if not valid_trade:
            for msg in error_msgs:
                st.caption(f"<span style='color:red'>{msg}</span>", unsafe_allow_html=True)
            st.button("🚫 无法开仓", disabled=True)
        else:
            if st.button("🚀 执行开仓 (Execute)", type="primary"):
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
                st.toast(f"✅ {symbol} 开仓成功！")
                st.rerun()

# 2. 持仓管理
st.subheader("⚡ 持仓管理 (Active Positions)")

active_pos = st.session_state.positions[st.session_state.positions['Status'] == 'Open']

if active_pos.empty:
    st.info("🧘 当前空仓，等待机会...")
else:
    for idx, row in active_pos.iterrows():
        with st.container():
            # 使用 HTML/CSS 渲染漂亮的卡片
            st.markdown(f"""
            <div class="trade-card">
                <div class="trade-header">
                    <div>
                        <span class="trade-symbol">{row['Symbol']}</span>
                        <span class="trade-tag">{row['Market'].split('(')[0]}</span>
                        <span style="color:#aaa; font-size:0.8em; margin-left:5px;">#{row['ID']}</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.8em; color:#888;">剩余持仓</span><br>
                        <span style="font-weight:bold; font-size:1.2em;">{int(row['Remaining_Qty'])}</span> <span style="color:#ccc;">/ {int(row['Initial_Qty'])}</span>
                    </div>
                </div>
                
                <div class="trade-reason">
                    📝 <b>入场理由:</b> {row['Entry_Reason']}
                </div>
                
                <div class="trade-stats">
                    <div class="stat-item"><span class="stat-label">💰 成本价</span><span class="stat-val">{row['Entry_Price']}</span></div>
                    <div class="stat-item"><span class="stat-label">🔴 止损价</span><span class="stat-val" style="color:#d9534f">{row['Stop_Price']}</span></div>
                    <div class="stat-item"><span class="stat-label">🟢 目标1</span><span class="stat-val" style="color:#2e7d32">{row['Target_1']}</span></div>
                    <div class="stat-item"><span class="stat-label">🚀 目标2</span><span class="stat-val" style="color:#2e7d32">{row['Target_2']}</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 操作区 (紧接卡片下方)
            c_op1, c_op2, c_op3 = st.columns([1.2, 1, 1.5])
            
            with c_op1:
                exit_price = st.number_input(f"卖出价格 ($)", key=f"p_{row['ID']}", value=row['Entry_Price'], step=0.01)
            
            with c_op2:
                default_sell = row['Remaining_Qty']
                if row['Remaining_Qty'] > 1:
                    default_sell = int(row['Remaining_Qty'] / 2)
                sell_qty = st.number_input(f"卖出数量", key=f"q_{row['ID']}", 
                                          min_value=1, max_value=int(row['Remaining_Qty']), 
                                          value=default_sell)
            
            with c_op3:
                # 预计算
                est_pl, _ = calculate_pnl(row['Market'], sell_qty, row['Entry_Price'], exit_price)
                pl_percent = (est_pl / (row['Entry_Price'] * sell_qty * (100 if "Option" in row['Market'] else 1))) * 100
                
                btn_type = "primary" if est_pl > 0 else "secondary"
                btn_icon = "📈" if est_pl > 0 else "📉"
                
                st.write("") # Spacer
                st.write("") # Spacer
                if st.button(f"{btn_icon} 确认卖出 ( ${est_pl:+.1f} | {pl_percent:+.1f}% )", key=f"btn_{row['ID']}", type=btn_type):
                    # 执行卖出
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
                        st.toast(f"✅ {row['Symbol']} 已全部平仓！")
                    else:
                        st.toast(f"✅ 部分减仓成功！剩余 {new_rem}")
                    
                    st.rerun()

# 3. 不过夜检查
st.markdown("### 🌙 收盘检查 (Night Watch)")
col_check_btn, col_check_res = st.columns([1, 3])
if col_check_btn.button("🧐 检查违规过夜单"):
    overnight_risks = []
    for idx, row in active_pos.iterrows():
        if "Option" in row['Market'] or "CBBC" in row['Market']:
            overnight_risks.append(f"🔴 {row['Symbol']} ({int(row['Remaining_Qty'])} 张/股)")
    
    if overnight_risks:
        st.error(f"❌ **严重违规！以下头寸禁止过夜，请立即平仓：**\n\n" + "\n".join(overnight_risks))
    else:
        st.success("✅ 检查通过：目前没有高风险过夜头寸。")

# 4. 历史明细
st.divider()
with st.expander("📜 历史执行流水 (Transaction History)", expanded=False):
    st.dataframe(st.session_state.executions.sort_values(by="Date", ascending=False), use_container_width=True)

    # 保存
    c1, c2 = st.columns(2)
    csv_exec = st.session_state.executions.to_csv(index=False).encode('utf-8')
    c1.download_button("💾 下载交易流水 (CSV)", csv_exec, "executions.csv", "text/csv")

    uploaded = c2.file_uploader("📂 加载备份 (Upload CSV)", type="csv")
    if uploaded and c2.button("确认加载"):
        try:
            st.session_state.executions = pd.read_csv(uploaded)
            st.success("加载成功！")
            st.rerun()
        except Exception as e:
            st.error(f"加载失败: {e}")
