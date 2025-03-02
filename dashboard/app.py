import streamlit as st
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="SubScan", page_icon="💳", layout="wide")

st.markdown("""
<style>
.main { background-color: #0f0f0f; }
.metric-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 1px solid #e94560;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.sub-card {
    background: #1a1a2e;
    border-left: 4px solid #e94560;
    border-radius: 8px;
    padding: 16px;
    margin: 8px 0;
}
h1 { color: #e94560 !important; }
</style>
""", unsafe_allow_html=True)

st.title("💳 SubScan")
st.markdown("**Drop your bank statement. See every subscription draining your account.**")
st.markdown("---")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("### Upload Statement")
    st.markdown("Supports: RBC, TD, Scotiabank, BMO, CIBC — CSV or PDF")
    uploaded = st.file_uploader("", type=["csv", "pdf"], label_visibility="collapsed")

with col2:
    st.markdown("### Supported Banks")
    for bank in ["🏦 RBC", "🏦 TD Bank", "🏦 Scotiabank", "🏦 BMO", "🏦 CIBC"]:
        st.markdown(f"- {bank}")

if uploaded:
    with st.spinner("Scanning for subscriptions..."):
        try:
            resp = httpx.post(f"{API_URL}/analyze", files={"file": (uploaded.name, uploaded.getvalue(), "application/octet-stream")}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    st.markdown("---")
    st.markdown("## 📊 Results")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Subscriptions Found", data["subscriptions_found"])
    c2.metric("Monthly Burn", f"${data['total_monthly_burn']:.2f}")
    c3.metric("Annual Burn", f"${data['total_annual_burn']:.2f}")
    c4.metric("Transactions Scanned", data["total_transactions"])

    st.markdown("---")

    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown("### 🔄 Your Subscriptions")
        for sub in data["subscriptions"]:
            savings_annual = sub["annual_cost"]
            st.markdown(f"""
            **{sub['name']}** — `{sub['category']}`
            | ${sub['monthly_cost']:.2f}/mo | ${sub['annual_cost']:.2f}/yr | {sub['frequency']} | Last: {sub['last_charge']}
            > Cancel this → save **${savings_annual:.2f}/year**
            ---
            """)

    with col_b:
        st.markdown("### 💰 Spend by Category")
        if data["category_breakdown"]:
            cat_df = pd.DataFrame(list(data["category_breakdown"].items()), columns=["Category", "Monthly ($)"])
            fig = px.pie(cat_df, names="Category", values="Monthly ($)", hole=0.4,
                        color_discrete_sequence=px.colors.sequential.RdBu)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🔥 Cancel Priority")
        subs_df = pd.DataFrame(data["subscriptions"])[["name", "monthly_cost", "annual_cost"]]
        fig2 = px.bar(subs_df.head(8), x="monthly_cost", y="name", orientation="h",
                     color="monthly_cost", color_continuous_scale="Reds",
                     labels={"monthly_cost": "$/month", "name": ""})
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("### 💡 If You Cancelled Everything")
    total_saved = data["total_annual_burn"]
    st.success(f"You'd save **${total_saved:.2f} per year** — that's **${total_saved/12:.2f} back in your pocket every month**")
else:
    st.info("Upload a bank statement above to get started. Your data never leaves your browser session.")
    st.markdown("### Example output:")
    sample = {
        "subscriptions_found": 8,
        "total_monthly_burn": 127.43,
        "total_annual_burn": 1529.16,
        "subscriptions": [
            {"name": "Adobe Creative Cloud", "monthly_cost": 54.99, "annual_cost": 659.88, "category": "Software", "frequency": "monthly", "last_charge": "2024-02-01"},
            {"name": "Netflix", "monthly_cost": 17.99, "annual_cost": 215.88, "category": "Entertainment", "frequency": "monthly", "last_charge": "2024-02-05"},
            {"name": "Spotify", "monthly_cost": 11.99, "annual_cost": 143.88, "category": "Music", "frequency": "monthly", "last_charge": "2024-02-03"},
            {"name": "LinkedIn Premium", "monthly_cost": 39.99, "annual_cost": 479.88, "category": "Professional", "frequency": "monthly", "last_charge": "2024-02-10"},
        ]
    }
    for sub in sample["subscriptions"]:
        st.markdown(f"**{sub['name']}** — ${sub['monthly_cost']}/mo — Save ${sub['annual_cost']:.2f}/yr if cancelled")
