# =========================================================
# DI + FRA Analysis Dashboard (Plotly + Widgets)
# For GitHub Deployment on Streamlit Cloud
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ---------------------------------------------------
# Streamlit Page Config
# ---------------------------------------------------
st.set_page_config(
    page_title="DI & FRA Dashboard",
    layout="wide",
)

st.title("📈 DI & FRA Dashboard (Plotly + Widgets)")

# ---------------------------------------------------
# File Upload
# ---------------------------------------------------
st.sidebar.header("⚙️ Controls")

uploaded = st.sidebar.file_uploader(
    "Upload DI & FRA file (CSV or Excel)",
    type=["csv", "xlsx"]
)

# ---------------------------------------------------
# Helper: detect date column
# ---------------------------------------------------
def detect_date_column(df):
    for col in df.columns:
        lower = str(col).lower()
        if "date" in lower:
            return col
        if lower.startswith("unnamed: 0"):
            return col
    return df.columns[0]

# ---------------------------------------------------
# Stop if no file uploaded
# ---------------------------------------------------
if uploaded is None:
    st.info("👈 Upload your DI/FRA dataset to begin.")
    st.stop()

# ---------------------------------------------------
# Load data
# ---------------------------------------------------
file_type = uploaded.name.lower()

if file_type.endswith(".csv"):
    df = pd.read_csv(uploaded)
else:
    df = pd.read_excel(uploaded)

date_col = detect_date_column(df)
df = df.rename(columns={date_col: "Date"})
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df[df["Date"].notna()].reset_index(drop=True)

# Detect DI and FRA columns
di_cols = [c for c in df.columns if str(c).startswith("F") and "-" not in str(c)]
fra_cols = [c for c in df.columns if "-" in str(c)]

# Numeric conversion
df[di_cols] = df[di_cols].apply(pd.to_numeric, errors="coerce")
df[fra_cols] = df[fra_cols].apply(pd.to_numeric, errors="coerce")

# ---------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------
st.sidebar.subheader("📅 Date Range Filter")

min_date = df["Date"].min()
max_date = df["Date"].max()

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date(),
)

start_date, end_date = date_range
df_filtered = df[(df["Date"] >= str(start_date)) & (df["Date"] <= str(end_date))]

st.sidebar.subheader("📊 Series Selection")

selected_di = st.sidebar.multiselect(
    "DI Contracts",
    options=di_cols,
    default=di_cols,
)

selected_fra = st.sidebar.multiselect(
    "FRA Spreads",
    options=fra_cols,
    default=fra_cols,
)

show_raw = st.sidebar.checkbox("Show Raw Data")
show_corr = st.sidebar.checkbox("Show Correlation Heatmap", value=False)

# ---------------------------------------------------
# Tabs
# ---------------------------------------------------
tab_overview, tab_di, tab_fra, tab_stats = st.tabs(
    ["📌 Overview", "📈 DI Curve", "📉 FRA Spreads", "📊 Analytics"]
)

# ---------------------------------------------------
# Overview Tab
# ---------------------------------------------------
with tab_overview:
    st.subheader("Dataset Summary")
    st.metric("Rows", len(df_filtered))
    st.metric("DI Series", len(di_cols))
    st.metric("FRA Series", len(fra_cols))

    if show_raw:
        st.dataframe(df_filtered)

# ---------------------------------------------------
# DI Tab
# ---------------------------------------------------
with tab_di:
    st.subheader("📈 DI Futures Over Time")

    if selected_di:
        fig = px.line(df_filtered, x="Date", y=selected_di)
        fig.update_layout(title="DI Contracts Time Series")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select DI contracts in sidebar.")

# ---------------------------------------------------
# FRA Tab
# ---------------------------------------------------
with tab_fra:
    st.subheader("📉 FRA Spread Evolution")

    if selected_fra:
        fig = px.line(df_filtered, x="Date", y=selected_fra)
        fig.update_layout(title="FRA Spread Time Series")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📎 FRA Volatility Ranking")
        fra_std = df_filtered[selected_fra].std().sort_values(ascending=False)
        fra_std_df = fra_std.reset_index()
        fra_std_df.columns = ["FRA", "StdDev"]
        fig2 = px.bar(fra_std_df, x="FRA", y="StdDev")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Select FRA spreads in sidebar.")

# ---------------------------------------------------
# Analytics Tab
# ---------------------------------------------------
with tab_stats:
    st.subheader("📊 Correlations & Descriptive Statistics")
    selected_cols = selected_di + selected_fra

    if show_corr and selected_cols:
        corr = df_filtered[selected_cols].corr()
        fig_corr = px.imshow(
            corr,
            text_auto=True,
            aspect="auto",
            title="Correlation Matrix"
        )
        st.plotly_chart(fig_corr, use_container_width=True)

    if selected_cols:
        st.write("### Descriptive Statistics")
        st.dataframe(df_filtered[selected_cols].describe())
    else:
        st.info("Select series to view analytics.")
