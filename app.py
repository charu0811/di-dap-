import streamlit as st
import pandas as pd

# Try to ensure plotly is available (works in single-file deployments)
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "plotly"], check=False)
    import plotly.express as px
    import plotly.graph_objects as go

# -----------------------
# Streamlit Page Config
# -----------------------
st.set_page_config(
    page_title="DI & FRA Dashboard",
    layout="wide",
)

st.title("📈 DI Futures & FRA Dashboard (CSV + Plotly)")

st.sidebar.header("⚙️ Controls")

uploaded = st.sidebar.file_uploader("Upload DI & FRA file (CSV)", type=["csv"])

# -----------------------
# Helper: detect date column
# -----------------------
def detect_date_column(df: pd.DataFrame) -> str | None:
    # Common patterns: 'Date', 'date', first unnamed col
    candidates = []
    for col in df.columns:
        lower = str(col).lower()
        if "date" in lower:
            candidates.append(col)
        if "unnamed: 0" == lower:
            candidates.append(col)
    if candidates:
        return candidates[0]
    # fallback: first column
    return df.columns[0] if len(df.columns) > 0 else None


if uploaded is None:
    st.info("👈 Upload a **CSV export** of your DI/FRA sheet to begin.")
    st.stop()

# -----------------------
# Load & clean data
# -----------------------
df = pd.read_csv(uploaded)

date_col = detect_date_column(df)
if date_col is None:
    st.error("Could not detect a date column. Ensure your first column is a date or named 'Date'.")
    st.stop()

df = df.rename(columns={date_col: "Date"})
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df[~df["Date"].isna()].reset_index(drop=True)

# Auto-detect DI and FRA columns
di_cols = [c for c in df.columns if str(c).startswith("F") and "-" not in str(c)]
fra_cols = [c for c in df.columns if "-" in str(c)]

# Convert to numeric
if di_cols:
    df[di_cols] = df[di_cols].apply(pd.to_numeric, errors="coerce")
if fra_cols:
    df[fra_cols] = df[fra_cols].apply(pd.to_numeric, errors="coerce")

# -----------------------
# Sidebar widgets
# -----------------------
st.sidebar.subheader("📅 Date range")

min_date = df["Date"].min()
max_date = df["Date"].max()

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date(),
)

if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date, end_date = min_date.date(), max_date.date()

mask = (df["Date"] >= pd.to_datetime(start_date)) & (df["Date"] <= pd.to_datetime(end_date))
df_filtered = df.loc[mask].copy()

st.sidebar.subheader("📊 Series selection")

selected_di = st.sidebar.multiselect(
    "DI contracts",
    options=di_cols,
    default=di_cols,
)

selected_fra = st.sidebar.multiselect(
    "FRA spreads",
    options=fra_cols,
    default=fra_cols,
)

st.sidebar.markdown("---")
show_raw = st.sidebar.checkbox("Show raw data", value=False)
show_corr = st.sidebar.checkbox("Show correlation heatmap", value=True)

# -----------------------
# Layout: Tabs
# -----------------------
tab_overview, tab_di, tab_fra, tab_stats = st.tabs(
    ["📌 Overview", "📈 DI Curve", "📉 FRA Spreads", "📊 Analytics"]
)

# -----------------------
# Overview Tab
# -----------------------
with tab_overview:
    st.subheader("Dataset Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Observations", len(df_filtered))
    col2.metric("DI Contracts", len(di_cols))
    col3.metric("FRA Spreads", len(fra_cols))

    st.markdown("**Detected DI contracts:**")
    st.write(di_cols if di_cols else "None")

    st.markdown("**Detected FRA spreads:**")
    st.write(fra_cols if fra_cols else "None")

    if show_raw:
        st.markdown("### Raw Data (Filtered by Date Range)")
        st.dataframe(df_filtered)

# -----------------------
# DI Tab
# -----------------------
with tab_di:
    st.subheader("📈 DI Futures Curve Over Time")

    if selected_di:
        fig_di = px.line(
            df_filtered,
            x="Date",
            y=selected_di,
            title="DI Futures (Selected Contracts)",
        )
        fig_di.update_layout(legend_title_text="Contracts")
        st.plotly_chart(fig_di, use_container_width=True)

        # Option: cross-section by date
        st.markdown("### DI Curve Snapshot (Cross-Section)")
        snapshot_date = st.date_input(
            "Select snapshot date for DI curve",
            value=min_date.date(),
            min_value=min_date.date(),
            max_value=max_date.date(),
            key="di_snapshot",
        )
        snap_mask = df["Date"] == pd.to_datetime(snapshot_date)
        if snap_mask.any():
            snap_row = df.loc[snap_mask, selected_di].iloc[0]
            fig_snap = px.line(
                x=selected_di,
                y=snap_row.values,
                markers=True,
                labels={"x": "Contract", "y": "Rate"},
                title=f"DI Curve Snapshot on {snapshot_date}",
            )
            st.plotly_chart(fig_snap, use_container_width=True)
        else:
            st.info("No data for that exact snapshot date.")
    else:
        st.info("Select at least one DI contract in the sidebar.")

# -----------------------
# FRA Tab
# -----------------------
with tab_fra:
    st.subheader("📉 FRA Spread Evolution")

    if selected_fra:
        fig_fra = px.line(
            df_filtered,
            x="Date",
            y=selected_fra,
            title="FRA Spreads (Selected Tenors)",
        )
        fig_fra.update_layout(legend_title_text="Spreads")
        st.plotly_chart(fig_fra, use_container_width=True)

        st.markdown("### FRA Volatility Ranking (Std Dev)")
        fra_std = df_filtered[selected_fra].std().sort_values(ascending=False)
        fra_std_df = fra_std.reset_index()
        fra_std_df.columns = ["FRA", "StdDev"]

        fig_std = px.bar(
            fra_std_df,
            x="FRA",
            y="StdDev",
            title="FRA Volatility Ranking",
        )
        st.plotly_chart(fig_std, use_container_width=True)
    else:
        st.info("Select at least one FRA spread in the sidebar.")

# -----------------------
# Analytics Tab
# -----------------------
with tab_stats:
    st.subheader("📊 Analytics & Correlations")

    if show_corr:
        # Use DI + FRA together for correlation
        numeric_cols = selected_di + selected_fra
        if numeric_cols:
            corr = df_filtered[numeric_cols].corr()

            fig_corr = px.imshow(
                corr,
                text_auto=True,
                aspect="auto",
                title="Correlation Matrix (DI & FRA)",
            )
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("Select DI/FRA series to compute correlations.")

    st.markdown("### Basic Descriptive Stats")
    if selected_di or selected_fra:
        st.dataframe(df_filtered[selected_di + selected_fra].describe())
    else:
        st.info("No series selected to show stats.")
