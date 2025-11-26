# =========================================================
# Auto-install required libraries (single-file deployment)
# =========================================================
import subprocess, sys

def ensure(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", package])

ensure("pandas")
ensure("numpy")
ensure("plotly")

# =========================================================
# Imports (after ensured)
# =========================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =========================================================
# Streamlit Page Config
# =========================================================
st.set_page_config(
    page_title="DI & FRA Dashboard",
    layout="wide",
)

st.title("📈 DI Futures & FRA Dashboard (CSV + Plotly + Widgets)")

# =========================================================
# File Upload
# =========================================================
st.sidebar.header("⚙️ Controls")

uploaded = st.sidebar.file_uploader("Upload DI & FRA CSV file", type=["csv"])

# =========================================================
# Helper: detect date column
# =========================================================
def detect_date_column(df):
    for col in df.columns:
        name = str(col).lower()
        if "date" in name:
            return col
        if name.startswith("unnamed: 0"):
            return col
    return df.columns[0]

# =========================================================
# Stop if no file uploaded
# =========================================================
if uploaded is None:
    st.info("👈 Upload a CSV export of your DI/FRA sheet to begin.")
    st.stop()

# =========================================================
# Load and clean data
# =========================================================
df = pd.read_csv(uploaded)

date_col = detect_date_column(df)
df = df.rename(columns={date_col: "Date"})
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df[df["Date"].notna()].reset_index(drop=True)

# Auto-detect columns
di_cols = [c for c in df.columns if str(c).startswith("F") and "-" not in str(c)]
fra_cols = [c for c in df.columns if "-" in str(c)]

# Convert numeric
if di_cols:
    df[di_cols] = df[di_cols].apply(pd.to_numeric, errors="coerce")
if fra_cols:
    df[fra_cols] = df[fra_cols].apply(pd.to_numeric, errors="coerce")

# =========================================================
# Sidebar Filters
# =========================================================
st.sidebar.subheader("📅 Date Range")

min_date = df["Date"].min()
max_date = df["Date"].max()

date_range = st.sidebar.date_input(
    "Filter dates",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date(),
)

if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date, end_date = min_date.date(), max_date.date()

df_filtered = df[(df["Date"] >= str(start_date)) & (df["Date"] <= str(end_date))]

st.sidebar.subheader("📊 Select Series")

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

show_raw = st.sidebar.checkbox("Show Raw Data", value=False)
show_corr = st.sidebar.checkbox("Show Correlation Heatmap", value=True)

# =========================================================
# Tabs
# =========================================================
tab_overview, tab_di, tab_fra, tab_stats = st.tabs(
    ["📌 Overview", "📈 DI Curve", "📉 FRA Spreads", "📊 Analytics"]
)

# =========================================================
# Overview
# =========================================================
with tab_overview:
    st.subheader("Dataset Summary")
    st.metric("Rows", len(df_filtered))
    st.metric("DI Series", len(di_cols))
    st.metric("FRA Series", len(fra_cols))

    st.write("### Detected DI Columns:")
    st.write(di_cols)

    st.write("### Detected FRA Columns:")
    st.write(fra_cols)

    if show_raw:
        st.write("### Raw Data")
        st.dataframe(df_filtered)

# =========================================================
# DI Tab
# =========================================================
with tab_di:
    st.subheader("📈 DI Futures Over Time")

    if selected_di:
        fig = px.line(df_filtered, x="Date", y=selected_di)
        fig.update_layout(title="DI Contracts Time Series")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select DI series in the sidebar.")

# =========================================================
# FRA Tab
# =========================================================
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
        st.info("Select FRA series in the sidebar.")

# =========================================================
# Analytics Tab
# =========================================================
with tab_stats:
    st.subheader("📊 Correlations & Stats")

    numeric_cols = selected_di + selected_fra

    if show_corr and numeric_cols:
        corr = df_filtered[numeric_cols].corr()
        fig_corr = px.imshow(corr, text_auto=True, aspect="auto", title="Correlation Matrix")
        st.plotly_chart(fig_corr, use_container_width=True)

    if numeric_cols:
        st.write("### Descriptive Statistics")
        st.dataframe(df_filtered[numeric_cols].describe())
    else:
        st.info("Select series to compute statistics.")
