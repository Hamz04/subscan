"""
SubScan - Streamlit Dashboard
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import httpx
import json

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="SubScan - Subscription Detector",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #1e1e2e, #2d2d44);
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #3d3d5c;
    text-align: center;
}
.danger-badge {
    background: #ff4444;
    color: white;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
}
.medium-badge {
    background: #ff9900;
    color: white;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
}
.low-badge {
    background: #00cc44;
    color: white;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

CATEGORY_COLORS = {
    "streaming": "#e50914",
    "music": "#1db954",
    "fitness": "#ff6b35",
    "software": "#0078d4",
    "gaming": "#107c10",
    "food": "#ff9900",
    "news": "#6c757d",
    "reading": "#8b5e3c",
    "learning": "#7b2d8b",
    "finance": "#00b4d8",
    "other": "#aaaaaa",
}

def render_sidebar():
    st.sidebar.image("https://img.icons8.com/fluency/96/bank-card-back-side.png", width=80)
    st.sidebar.title("SubScan 💳")
    st.sidebar.markdown("*Stop paying for things you forgot about.*")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### How it works")
    st.sidebar.markdown("1. Download your bank statement as CSV or PDF")
    st.sidebar.markdown("2. Upload it below")
    st.sidebar.markdown("3. See every subscription instantly")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Supported Banks")
    banks = {"RBC": "✅", "TD": "✅", "Scotiabank": "✅", "BMO": "✅", "CIBC": "✅"}
    for bank, status in banks.items():
        st.sidebar.markdown(f"{status} {bank}")
    st.sidebar.markdown("---")
    st.sidebar.markdown("🔒 **Your data never leaves your device**")

def render_hero():
    st.markdown("## 💳 SubScan — Subscription Detector")
    st.markdown("*Upload your bank statement. Find every subscription bleeding your account.*")
    st.markdown("---")

def render_upload():
    uploaded = st.file_uploader(
        "Drop your bank statement here",
        type=["csv", "pdf", "xlsx"],
        help="Supports RBC, TD, Scotiabank, BMO, CIBC formats"
    )
    return uploaded

def render_metrics(savings: dict):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Monthly Subscriptions", f"${savings.get('total_monthly_spend', 0):.2f}", delta=None)
    with col2:
        st.metric("Annual Total", f"${savings.get('total_annual_spend', 0):.2f}", delta=None)
    with col3:
        st.metric("Potential Monthly Savings", f"${savings.get('potential_monthly_savings', 0):.2f}", delta=f"{savings.get('savings_percentage', 0)}%")
    with col4:
        st.metric("Subscriptions Found", savings.get("total_subscriptions", 0))

def render_category_chart(subscriptions: list):
    if not subscriptions:
        return
    df = pd.DataFrame(subscriptions)
    category_totals = df.groupby("category")["monthly_cost"].sum().reset_index()
    colors = [CATEGORY_COLORS.get(cat, "#aaaaaa") for cat in category_totals["category"]]
    fig = px.pie(
        category_totals,
        values="monthly_cost",
        names="category",
        title="Monthly Spend by Category",
        color_discrete_sequence=colors,
        hole=0.4
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3)
    )
    st.plotly_chart(fig, use_container_width=True)

def render_subscription_table(subscriptions: list):
    if not subscriptions:
        st.info("No subscriptions detected.")
        return
    st.markdown("### All Detected Subscriptions")
    df = pd.DataFrame(subscriptions)
    for _, row in df.iterrows():
        priority = row.get("priority", "Low")
        badge_class = {"High": "danger-badge", "Medium": "medium-badge", "Low": "low-badge"}.get(priority, "low-badge")
        with st.expander(f"**{row['service']}** — ${row['monthly_cost']:.2f}/mo"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Monthly", f"${row['monthly_cost']:.2f}")
            c2.metric("Annual", f"${row['annual_cost']:.2f}")
            c3.metric("Times Charged", row['times_charged'])
            st.markdown(f"**Category:** {row['category'].title()}")
            st.markdown(f"**Last Charged:** {row['last_charged']}")
            st.markdown(f"**Recommendation:** {row['recommendation']}")
            st.markdown(f"<span class='{badge_class}'>{priority} Priority</span>", unsafe_allow_html=True)

def render_savings_banner(savings: dict):
    monthly = savings.get("potential_monthly_savings", 0)
    annual = savings.get("potential_annual_savings", 0)
    count = savings.get("subscriptions_to_cancel", 0)
    if monthly > 0:
        st.success(f"💰 Cancel {count} low-priority subscriptions → Save **${monthly:.2f}/month** (${annual:.2f}/year)")

def render_bar_chart(subscriptions: list):
    if not subscriptions:
        return
    df = pd.DataFrame(subscriptions).head(15)
    colors = [CATEGORY_COLORS.get(cat, "#aaaaaa") for cat in df["category"]]
    fig = go.Figure(go.Bar(
        x=df["monthly_cost"],
        y=df["service"],
        orientation="h",
        marker_color=colors,
        text=[f"${v:.2f}" for v in df["monthly_cost"]],
        textposition="outside"
    ))
    fig.update_layout(
        title="Top Subscriptions by Monthly Cost",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        xaxis_title="Monthly Cost ($)",
        yaxis=dict(autorange="reversed"),
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

def analyze_file(uploaded_file):
    with st.spinner("Analyzing your statement..."):
        try:
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            response = httpx.post(f"{API_URL}/api/analyze", files=files, timeout=30)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            st.error(f"Analysis failed: {e.response.text}")
            return None
        except Exception as e:
            st.error(f"Could not connect to backend: {e}")
            return None

def main():
    render_sidebar()
    render_hero()
    uploaded = render_upload()
    if uploaded:
        result = analyze_file(uploaded)
        if result:
            savings = result.get("savings", {})
            subscriptions = result.get("subscriptions", [])
            bank = result.get("bank_detected", "unknown").upper()
            total_tx = result.get("total_transactions", 0)
            st.info(f"Detected bank: **{bank}** | Transactions analyzed: **{total_tx}**")
            render_metrics(savings)
            render_savings_banner(savings)
            st.markdown("---")
            col1, col2 = st.columns([1, 1])
            with col1:
                render_category_chart(subscriptions)
            with col2:
                render_bar_chart(subscriptions)
            st.markdown("---")
            render_subscription_table(subscriptions)
    else:
        st.markdown("### 👆 Upload a bank statement to get started")
        st.markdown("Download your statement from your bank's website as a CSV or PDF, then drag and drop it above.")
        st.markdown("---")
        st.markdown("#### Example results:")
        demo_subs = [
            {"Service": "Netflix", "Monthly": "$15.49", "Annual": "$185.88", "Priority": "Keep"},
            {"Service": "Duolingo (forgotten)", "Monthly": "$6.99", "Annual": "$83.88", "Priority": "Cancel"},
            {"Service": "Adobe CC", "Monthly": "$54.99", "Annual": "$659.88", "Priority": "Keep"},
            {"Service": "EA Play (unused)", "Monthly": "$4.99", "Annual": "$59.88", "Priority": "Cancel"},
        ]
        st.table(pd.DataFrame(demo_subs))

if __name__ == "__main__":
    main()
