import streamlit as st
import pandas as pd
from datetime import datetime

# --- 📱 移动优先配置 (Mobile First Config) ---
st.set_page_config(page_title="Thorp's Edge Mobile", layout="centered", page_icon="⚡")

# --- 🎨 极简 UI 样式 (Minimalist CSS) ---
st.markdown("""
<style>
    /* 全局移动端优化 */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 大按钮，适合手指点击 */
    .stButton > button {
        width: 100%;
        height: 3.5rem;
        font-size: 1.2rem;
        font-weight: bold;
        border-radius: 12px;
    }
    
    /* 关键数据卡片 */
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #333; }
    .metric-label { font-size: 0.9rem; color: #666; }
    
    /* 信号源标签 */
    .source-tag-self { background-color: #e6f4ea; color: #1e8e3e; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold;}
    .source-tag-feng { background-color: #fce8e6; color: #d93025; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold;}
    
</style>
""", unsafe_allow_html=True)

# --- ⚙️ 核心参数 (Core Logic) ---
MAX_LOSS_PER_TRADE = 500.0  # Cathy: 单笔最大亏损 $500
STOP_LOSS_PCT = 0.20        # Cathy: 20% 止损
MULTIPLIER_OPT = 100        # 期权乘数

# --- 💾 数据初始化 ---
if 'positions' not in st.session_state:
    st.session_state.positions = pd.DataFrame(columns=[
        "ID", "Date", "Symbol", "Type", "Source", 
        "Entry_Price", "Qty", "Stop_Price", "Status"
    ])

# --- 🧠 智能计算核心 (The Brain) ---
def calculate_trade_plan(price, source, asset_type):
    # 1. 确定风险敞口
    allowed_risk = MAX_LOSS_PER_TRADE
    if source == "Feng Ge (跟单)":
        allowed_risk = MAX_LOSS_PER_TRADE * 0.5  # ⚠️ 别人的单子，风险减半
    
    # 2. 计算止损价 (固定 20%)
    stop_price = price * (1 - STOP_LOSS_PCT)
    risk_per_unit = price * STOP_LOSS_PCT
    
    # 3. 计算数量
    multiplier = MULTIPLIER_OPT if asset_type == "Option" else 1
    
    # 公式: Qty * Multiplier * Risk_Per_Share <= Allowed_Risk
    # Qty <= Allowed_Risk / (Multiplier * Risk_Per_Share)
    raw_qty = allowed_risk / (multiplier * risk_per_unit)
    
    # 取整 (向下取整，保守)
    qty = max(1, int(raw_qty))
    
    # 如果是正股，可能需要调整最小单位 (如港股一手，美股无所谓)
    # 这里为了极简，美股期权/正股直接按计算值
    
    # 4. 计算总投入
    total_cost = qty * price * multiplier
    
    return qty, stop_price, total_cost, allowed_risk

# --- 📱 界面布局 ---

# 1. 抬头 & 状态
today_pl = 0.0 # 暂时不从历史读，保持极简，或者只显示今日
st.markdown("### ⚡ 极速交易终端 (Mobile)")

# 2. 极简输入区 (Zero Friction Input)
with st.container():
    st.info("🤖 **信号处理器**")
    
    # 第一行：代码 + 价格
    c1, c2 = st.columns([1, 1])
    symbol = c1.text_input("代码", value="", placeholder="NVDA").upper()
    price = c2.number_input("现价 ($)", min_value=0.0, value=0.0, step=0.1)
    
    # 第二行：类型 + 来源
    c3, c4 = st.columns([1, 1])
    asset_type = c3.selectbox("类型", ["Option", "Stock"], index=0)
    source = c4.selectbox("信号来源", ["自研 (Self)", "Feng Ge (跟单)"])
    
    # 自动计算展示区
    if symbol and price > 0:
        qty, stop_p, cost, risk_limit = calculate_trade_plan(price, source, asset_type)
        
        # 💡 智能建议卡片
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid {'#d93025' if source == 'Feng Ge (跟单)' else '#1e8e3e'}">
            <div style="font-size:1.1rem; margin-bottom:5px;">📢 交易建议 ({source})</div>
            <div style="display:flex; justify-content:space-around; align-items:center;">
                <div>
                    <div class="metric-label">买入数量</div>
                    <div class="metric-value" style="color:#0068c9">{qty} <span style="font-size:1rem">{'张' if asset_type=='Option' else '股'}</span></div>
                </div>
                <div>
                    <div class="metric-label">止损价格</div>
                    <div class="metric-value" style="color:#d9534f">${stop_p:.2f}</div>
                </div>
            </div>
            <div style="margin-top:10px; font-size:0.85rem; color:#888;">
                投入本金: ${cost:.0f} | 潜在亏损: <span style="color:#d9534f">-${cost * STOP_LOSS_PCT:.0f}</span> (限额: ${risk_limit:.0f})
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 极速下单按钮
        if st.button(f"✅ 立即执行 (买入 {symbol})", type="primary"):
            new_pos = {
                "ID": datetime.now().strftime("%H%M%S"),
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Symbol": symbol,
                "Type": asset_type,
                "Source": source,
                "Entry_Price": price,
                "Qty": qty,
                "Stop_Price": stop_p,
                "Status": "Open"
            }
            st.session_state.positions = pd.concat([st.session_state.positions, pd.DataFrame([new_pos])], ignore_index=True)
            st.toast(f"🚀 已买入 {qty} {asset_type} {symbol}")
            st.rerun()

# 3. 持仓管理 (Active Positions)
st.markdown("### 💼 持仓 (Active)")

active = st.session_state.positions[st.session_state.positions['Status'] == 'Open']

if active.empty:
    st.caption("空仓也是一种策略 🧘")
else:
    for idx, row in active.iterrows():
        with st.expander(f"{row['Symbol']} {row['Type']} (Qty: {row['Qty']})", expanded=True):
            # 顶部信息栏
            c_tag, c_price = st.columns([2, 1])
            source_class = "source-tag-self" if "Self" in row['Source'] else "source-tag-feng"
            source_label = "自研" if "Self" in row['Source'] else "Feng Ge"
            
            c_tag.markdown(f"<span class='{source_class}'>{source_label}</span> <span style='color:#666'>@{row['Entry_Price']}</span>", unsafe_allow_html=True)
            
            # 止损线提醒
            st.markdown(f"🛑 止损: **${row['Stop_Price']:.2f}**")
            
            # 卖出操作区
            st.write("---")
            c_sell_price = st.number_input("卖出价", key=f"sp_{row['ID']}", value=float(row['Entry_Price']))
            
            if st.button(f"📉 卖出平仓", key=f"btn_sell_{row['ID']}"):
                # 简单处理：全部平仓 (移动端简化逻辑)
                st.session_state.positions.at[idx, 'Status'] = 'Closed'
                
                # 计算盈亏
                multiplier = MULTIPLIER_OPT if row['Type'] == "Option" else 1
                pnl = (c_sell_price - row['Entry_Price']) * row['Qty'] * multiplier
                
                st.toast(f"✅ 平仓完成！盈亏: ${pnl:.1f}")
                st.rerun()

# 4. 底部调试/数据链接 (可选)
with st.expander("🛠️ 数据管理"):
    st.dataframe(st.session_state.positions)
