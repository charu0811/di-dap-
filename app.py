import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="DI & FRA Dashboard", layout="wide")

st.title("📈 DI Futures & FRA Spread Dashboard")

uploaded = st.file_uploader("Upload DI & FRA Excel file", type=["xlsx"])

if uploaded is not None:

    # Load Excel
    df = pd.read_excel(uploaded)

    # Rename and clean Date column
    if "Unnamed: 0" in df.columns:
        df = df.rename(columns={"Unnamed: 0": "Date"})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Drop non-data rows
    df = df[~df["Date"].isna()].reset_index(drop=True)

    # Auto-detect DI and FRA columns
    di_cols = [c for c in df.columns if c.startswith("F") and "-" not in c]
    fra_cols = [c for c in df.columns if "-" in c]

    # Convert numeric columns
    df[di_cols] = df[di_cols].apply(pd.to_numeric, errors="coerce")
    df[fra_cols] = df[fra_cols].apply(pd.to_numeric, errors="coerce")

    st.subheader("✅ Data Loaded Successfully")
    st.write(f"**DI Contracts Detected:** {len(di_cols)}")
    st.write(f"**FRA Spreads Detected:** {len(fra_cols)}")

    # =========================
    # DI Chart
    # =========================
    st.subheader("📊 DI Futures Curve Over Time")

    fig_di = px.line(df, x="Date", y=di_cols)
    st.plotly_chart(fig_di, use_container_width=True)

    # =========================
    # FRA Chart
    # =========================
    st.subheader("📉 FRA Spread Evolution")

    fig_fra = px.line(df, x="Date", y=fra_cols)
    st.plotly_chart(fig_fra, use_container_width=True)

    # =========================
    # Statistics
    # =========================
    st.subheader("📎 FRA Volatility Ranking")

    fra_std = df[fra_cols].std().sort_values(ascending=False)
    st.bar_chart(fra_std)

else:
    st.info("👆 Upload an Excel file to get started.")
