"""
Hoichoi Audio Analytics Dashboard
Streamlit app for Listened_ event analysis from Google Analytics 4.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from modules.data_processing import (
    fetch_summary_metrics,
    fetch_daily_trend,
    fetch_by_content,
    fetch_content_by_date,
    fetch_by_country,
    fetch_content_by_country,
    get_filter_options,
    prepare_chatbot_context,
)
from modules.charts import (
    daily_trend_chart,
    metric_comparison_chart,
    top_content_bar_chart,
    country_bar_chart,
    country_choropleth,
    content_trend_chart,
    donut_chart,
)
from modules.chatbot import get_chatbot_response, get_suggested_questions
from modules.constants import COLORS, UNREGISTERED_DIMENSIONS

# ─── Page Config ───
st.set_page_config(
    page_title="Hoichoi Audio Analytics",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #6C3483;
        margin-bottom: 0;
    }
    .sub-title {
        font-size: 1rem;
        color: #888;
        margin-top: -10px;
    }
    .metric-card {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        border: 1px solid #6C3483;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #6C3483;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #AAA;
        margin-top: 5px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Sidebar ───
with st.sidebar:
    st.markdown("## 🎧 Hoichoi Audio")
    st.markdown("**Listened_ Event Dashboard**")
    st.divider()

    # Date range
    st.markdown("### 📅 Date Range")
    col1, col2 = st.columns(2)
    default_end = datetime.now().date()
    default_start = default_end - timedelta(days=30)

    with col1:
        start_date = st.date_input("Start", value=default_start)
    with col2:
        end_date = st.date_input("End", value=default_end)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    st.divider()

    # Fetch filter options
    try:
        content_options, country_options = get_filter_options(start_str, end_str)
    except Exception:
        content_options, country_options = [], []

    # Content filter
    st.markdown("### 🎵 Content Filter")
    selected_content = st.multiselect(
        "Select content titles",
        options=content_options,
        default=[],
        placeholder="All content",
    )

    # Country filter
    st.markdown("### 🌍 Geography Filter")
    selected_countries = st.multiselect(
        "Select countries",
        options=country_options,
        default=[],
        placeholder="All countries",
    )

    st.divider()

    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

    # Warning about unregistered dimensions
    with st.expander("⚠️ Unregistered Dimensions"):
        st.warning(
            "The following event parameters are **not yet registered** as "
            "GA4 custom dimensions and cannot be queried:"
        )
        for name, dim in UNREGISTERED_DIMENSIONS.items():
            st.code(name)
        st.info(
            "Register them in GA4 Admin → Custom Definitions → "
            "Create Custom Dimension (Event scope)."
        )

    st.divider()
    st.caption("Data may be sampled by GA4 (~2.7%)")
    st.caption(f"Period: {start_str} to {end_str}")


# ─── Convert filters to tuples for caching ───
content_filter = tuple(selected_content) if selected_content else None
country_filter = tuple(selected_countries) if selected_countries else None


# ─── Header ───
st.markdown('<p class="main-title">🎧 Hoichoi Audio Analytics</p>', unsafe_allow_html=True)
st.markdown(
    f'<p class="sub-title">Listened_ Event Dashboard | {start_str} to {end_str}</p>',
    unsafe_allow_html=True,
)

# ─── Tabs ───
tab_overview, tab_content, tab_geo, tab_detailed, tab_chat = st.tabs(
    ["📊 Overview", "🎵 Content Analysis", "🌍 Geography", "📋 Detailed Data", "💬 Ask the Data"]
)


# ═══════════════════════════════════════
# TAB 1: OVERVIEW
# ═══════════════════════════════════════
with tab_overview:
    try:
        # Fetch data
        summary = fetch_summary_metrics(start_str, end_str, content_filter, country_filter)
        daily_df = fetch_daily_trend(start_str, end_str, content_filter, country_filter)

        # KPI Cards
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.metric("Total Events", f"{summary['total_events']:,}")
        with k2:
            st.metric("Distinct Users", f"{summary['total_users']:,}")
        with k3:
            st.metric("New Users", f"{summary['new_users']:,}")
        with k4:
            st.metric("Active Users", f"{summary['active_users']:,}")
        with k5:
            st.metric("Avg Events/Day", f"{summary['avg_events_per_day']:,}")

        st.divider()

        # Daily Trend
        if not daily_df.empty:
            col_chart, col_selector = st.columns([4, 1])
            with col_selector:
                metric_choice = st.selectbox(
                    "Metric",
                    ["eventCount", "totalUsers", "newUsers", "activeUsers"],
                    format_func=lambda x: {
                        "eventCount": "Total Events",
                        "totalUsers": "Distinct Users",
                        "newUsers": "New Users",
                        "activeUsers": "Active Users",
                    }[x],
                    key="overview_metric",
                )
            with col_chart:
                st.plotly_chart(
                    daily_trend_chart(daily_df, metric_choice),
                    use_container_width=True,
                )

            st.divider()

            # Multi-metric comparison
            st.plotly_chart(
                metric_comparison_chart(daily_df), use_container_width=True
            )
        else:
            st.warning("No data found for the selected filters and date range.")

    except Exception as e:
        st.error(f"Error loading overview: {e}")


# ═══════════════════════════════════════
# TAB 2: CONTENT ANALYSIS
# ═══════════════════════════════════════
with tab_content:
    try:
        content_df = fetch_by_content(start_str, end_str, country_filter)

        if not content_df.empty:
            st.markdown(f"### 📊 {len(content_df)} Content Titles Found")

            # Top content bar chart
            col_bar, col_opts = st.columns([4, 1])
            with col_opts:
                content_metric = st.selectbox(
                    "Metric",
                    ["eventCount", "totalUsers", "newUsers", "activeUsers"],
                    format_func=lambda x: {
                        "eventCount": "Total Events",
                        "totalUsers": "Distinct Users",
                        "newUsers": "New Users",
                        "activeUsers": "Active Users",
                    }[x],
                    key="content_metric",
                )
                top_n = st.slider("Top N", 5, 30, 15, key="content_top_n")
            with col_bar:
                st.plotly_chart(
                    top_content_bar_chart(content_df, content_metric, top_n),
                    use_container_width=True,
                )

            st.divider()

            # Content trend comparison
            st.markdown("### 📈 Content Trend Comparison")
            top_titles = content_df["content_title"].head(20).tolist()
            selected_titles = st.multiselect(
                "Select titles to compare",
                options=top_titles,
                default=top_titles[:3],
                key="content_trend_titles",
            )

            if selected_titles:
                trend_df = fetch_content_by_date(
                    start_str, end_str, tuple(selected_titles), country_filter
                )
                if not trend_df.empty:
                    st.plotly_chart(
                        content_trend_chart(trend_df, selected_titles, content_metric),
                        use_container_width=True,
                    )

            st.divider()

            # Full data table
            st.markdown("### 📋 Full Content Data")
            display_df = content_df.rename(
                columns={
                    "content_title": "Content Title",
                    "eventCount": "Events",
                    "totalUsers": "Distinct Users",
                    "newUsers": "New Users",
                    "activeUsers": "Active Users",
                    "events_per_user": "Events/User",
                }
            )
            st.dataframe(
                display_df,
                use_container_width=True,
                height=500,
                column_config={
                    "Events": st.column_config.NumberColumn(format="%d"),
                    "Distinct Users": st.column_config.NumberColumn(format="%d"),
                    "New Users": st.column_config.NumberColumn(format="%d"),
                    "Active Users": st.column_config.NumberColumn(format="%d"),
                    "Events/User": st.column_config.NumberColumn(format="%.2f"),
                },
            )

            # Download button
            csv = content_df.to_csv(index=False)
            st.download_button(
                "📥 Download Content Data (CSV)",
                csv,
                "hoichoi_content_data.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.warning("No content data found for the selected filters.")

    except Exception as e:
        st.error(f"Error loading content analysis: {e}")


# ═══════════════════════════════════════
# TAB 3: GEOGRAPHY
# ═══════════════════════════════════════
with tab_geo:
    try:
        country_df = fetch_by_country(start_str, end_str, content_filter)

        if not country_df.empty:
            st.markdown(f"### 🌍 {len(country_df)} Countries")

            # Metric selector
            geo_metric = st.selectbox(
                "Metric",
                ["eventCount", "totalUsers", "newUsers", "activeUsers"],
                format_func=lambda x: {
                    "eventCount": "Total Events",
                    "totalUsers": "Distinct Users",
                    "newUsers": "New Users",
                    "activeUsers": "Active Users",
                }[x],
                key="geo_metric",
            )

            # Choropleth
            st.plotly_chart(
                country_choropleth(country_df, geo_metric),
                use_container_width=True,
            )

            # Bar chart and donut side by side
            col_bar, col_donut = st.columns([3, 2])
            with col_bar:
                st.plotly_chart(
                    country_bar_chart(country_df, geo_metric),
                    use_container_width=True,
                )
            with col_donut:
                st.plotly_chart(
                    donut_chart(
                        country_df.head(8),
                        "country",
                        geo_metric,
                        f"Share by Country ({geo_metric})",
                    ),
                    use_container_width=True,
                )

            st.divider()

            # Content x Country
            st.markdown("### 🎵 Top Content by Country")
            content_country_df = fetch_content_by_country(
                start_str, end_str, content_filter, country_filter
            )
            if not content_country_df.empty:
                pivot_df = content_country_df.pivot_table(
                    index="content_title",
                    columns="country",
                    values="eventCount",
                    aggfunc="sum",
                    fill_value=0,
                )
                pivot_df["Total"] = pivot_df.sum(axis=1)
                pivot_df = pivot_df.sort_values("Total", ascending=False).head(20)
                st.dataframe(pivot_df, use_container_width=True, height=500)

            # Download
            csv = country_df.to_csv(index=False)
            st.download_button(
                "📥 Download Geography Data (CSV)",
                csv,
                "hoichoi_geography_data.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.warning("No geography data found for the selected filters.")

    except Exception as e:
        st.error(f"Error loading geography: {e}")


# ═══════════════════════════════════════
# TAB 4: DETAILED DATA
# ═══════════════════════════════════════
with tab_detailed:
    try:
        st.markdown("### 📋 Content x Date Detailed View")
        st.info("This shows every content title × date combination with full metrics.")

        detail_df = fetch_content_by_date(
            start_str, end_str, content_filter, country_filter
        )

        if not detail_df.empty:
            # Add computed columns
            detail_df["events_per_user"] = (
                detail_df["eventCount"] / detail_df["activeUsers"].replace(0, 1)
            ).round(2)

            # Summary stats
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Rows", f"{len(detail_df):,}")
            with c2:
                st.metric("Unique Titles", f"{detail_df['content_title'].nunique():,}")
            with c3:
                st.metric("Date Range", f"{detail_df['date'].min().strftime('%b %d')} - {detail_df['date'].max().strftime('%b %d')}")

            st.divider()

            # Display
            display_detail = detail_df.rename(
                columns={
                    "content_title": "Content Title",
                    "date": "Date",
                    "eventCount": "Events",
                    "totalUsers": "Distinct Users",
                    "newUsers": "New Users",
                    "activeUsers": "Active Users",
                    "events_per_user": "Events/User",
                }
            )

            st.dataframe(
                display_detail,
                use_container_width=True,
                height=600,
                column_config={
                    "Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
                    "Events": st.column_config.NumberColumn(format="%d"),
                    "Distinct Users": st.column_config.NumberColumn(format="%d"),
                    "New Users": st.column_config.NumberColumn(format="%d"),
                    "Active Users": st.column_config.NumberColumn(format="%d"),
                    "Events/User": st.column_config.NumberColumn(format="%.2f"),
                },
            )

            # Download
            csv = detail_df.to_csv(index=False)
            st.download_button(
                "📥 Download Full Detail (CSV)",
                csv,
                "hoichoi_content_date_detail.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.warning("No detailed data found for the selected filters.")

    except Exception as e:
        st.error(f"Error loading detailed data: {e}")


# ═══════════════════════════════════════
# TAB 5: CHATBOT
# ═══════════════════════════════════════
with tab_chat:
    st.markdown("### 💬 Ask the Data")
    st.markdown(
        "Ask questions about your Hoichoi audio listening data. "
        "The AI analyst has access to all the dashboard data."
    )

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Prepare context from current data
    try:
        chat_summary = fetch_summary_metrics(start_str, end_str, content_filter, country_filter)
        chat_daily = fetch_daily_trend(start_str, end_str, content_filter, country_filter)
        chat_content = fetch_by_content(start_str, end_str, country_filter)
        chat_country = fetch_by_country(start_str, end_str, content_filter)
        data_context = prepare_chatbot_context(
            chat_summary, chat_daily, chat_content, chat_country
        )
    except Exception:
        data_context = "Error loading data context. Please check your GA4 connection."

    # Suggested questions
    with st.expander("💡 Suggested Questions", expanded=False):
        suggestions = get_suggested_questions()
        cols = st.columns(2)
        for i, q in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(q, key=f"suggest_{i}", use_container_width=True):
                    st.session_state.pending_question = q

    st.divider()

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    prompt = st.chat_input("Ask a question about your listening data...")

    # Check for pending question from suggestions
    if hasattr(st.session_state, "pending_question") and st.session_state.pending_question:
        prompt = st.session_state.pending_question
        st.session_state.pending_question = None

    if prompt:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing data..."):
                response = get_chatbot_response(
                    prompt, data_context, st.session_state.chat_history[:-1]
                )
                st.markdown(response)

        # Save assistant response
        st.session_state.chat_history.append(
            {"role": "assistant", "content": response}
        )

    # Clear chat button
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
