"""
Hoichoi Audio Analytics Dashboard
Single-page Streamlit dashboard for Listened_ event analysis from GA4.
Enriched with audio metadata from Google Sheets (show name, genre).
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from modules.data_processing import (
    fetch_summary_metrics,
    fetch_daily_trend,
    fetch_by_content,
    fetch_by_country,
    get_filter_options,
    prepare_chatbot_context,
)
from modules.charts import (
    daily_trend_chart,
    dual_axis_users_chart,
    show_grouped_bar_chart,
    episode_drilldown_chart,
    donut_chart,
    country_choropleth,
    country_bar_chart,
)
from modules.chatbot import get_chatbot_response, get_suggested_questions
from modules.constants import COLORS, UNREGISTERED_DIMENSIONS
from modules.gsheet_client import fetch_audio_metadata, enrich_with_metadata

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
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─── Load Audio Metadata (cached) ───
metadata_df = fetch_audio_metadata()

show_name_options = sorted(metadata_df["show_name"].dropna().unique().tolist()) if not metadata_df.empty and "show_name" in metadata_df.columns else []
genre_options = sorted(metadata_df["genre"].dropna().unique().tolist()) if not metadata_df.empty and "genre" in metadata_df.columns else []


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

    # Show filter
    st.markdown("### 📺 Show Filter")
    selected_shows = st.multiselect(
        "Select shows",
        options=show_name_options,
        default=[],
        placeholder="All shows",
    )

    # Genre filter
    st.markdown("### 🎭 Genre Filter")
    selected_genres = st.multiselect(
        "Select genres",
        options=genre_options,
        default=[],
        placeholder="All genres",
    )

    st.divider()

    # Country filter
    try:
        _, country_options = get_filter_options(start_str, end_str)
    except Exception:
        country_options = []

    st.markdown("### 🌍 Geography Filter")
    selected_countries = st.multiselect(
        "Select countries",
        options=country_options,
        default=[],
        placeholder="All countries",
    )

    st.divider()

    # Metadata status
    if not metadata_df.empty:
        st.success(f"📋 {len(metadata_df)} episodes mapped")
    else:
        st.warning("⚠️ Could not load audio metadata")

    if st.button("🔄 Refresh Data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(f"Period: {start_str} to {end_str}")


# ─── Resolve filters ───
def resolve_metadata_filters(shows, genres, metadata):
    if metadata.empty or (not shows and not genres):
        return None
    mask = pd.Series(True, index=metadata.index)
    if shows:
        mask &= metadata["show_name"].isin(shows)
    if genres:
        mask &= metadata["genre"].isin(genres)
    episodes = metadata.loc[mask, "ep_name"].tolist()
    return episodes if episodes else None


resolved_content = resolve_metadata_filters(selected_shows, selected_genres, metadata_df)
content_filter = tuple(resolved_content) if resolved_content else None
country_filter = tuple(selected_countries) if selected_countries else None


# ═══════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════
st.markdown('<p class="main-title">🎧 Hoichoi Audio Analytics</p>', unsafe_allow_html=True)
st.markdown(
    f'<p class="sub-title">Listened_ Event Dashboard | {start_str} to {end_str}</p>',
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════
# SECTION 1: OVERVIEW KPIs + DAILY CHARTS
# ═══════════════════════════════════════════════
try:
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

    # Two charts side by side
    if not daily_df.empty:
        col_left, col_right = st.columns(2)
        with col_left:
            st.plotly_chart(
                daily_trend_chart(daily_df, "eventCount"),
                use_container_width=True,
            )
        with col_right:
            st.plotly_chart(
                dual_axis_users_chart(daily_df),
                use_container_width=True,
            )
    else:
        st.warning("No data found for the selected filters and date range.")

except Exception as e:
    st.error(f"Error loading overview: {e}")


# ═══════════════════════════════════════════════
# SECTION 2: SHOW-LEVEL CONTENT ANALYTICS
# ═══════════════════════════════════════════════
st.divider()
st.markdown("## 📺 Content Analytics — By Show")

try:
    content_df = fetch_by_content(start_str, end_str, country_filter)
    content_df = enrich_with_metadata(content_df, metadata_df)

    # Apply show/genre filters
    if not content_df.empty:
        if selected_shows and "show_name" in content_df.columns:
            content_df = content_df[content_df["show_name"].isin(selected_shows)]
        if selected_genres and "genre" in content_df.columns:
            content_df = content_df[content_df["genre"].isin(selected_genres)]

    if not content_df.empty and "show_name" in content_df.columns:
        # Aggregate to show level
        show_agg = content_df.groupby("show_name", as_index=False).agg({
            "eventCount": "sum",
            "totalUsers": "sum",
            "activeUsers": "sum",
            "newUsers": "sum",
        }).sort_values("eventCount", ascending=False)

        # KPIs
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Total Shows", show_agg["show_name"].nunique())
        with sc2:
            st.metric("Total Episodes", len(content_df))
        with sc3:
            if "genre" in content_df.columns:
                st.metric("Genres", content_df["genre"].nunique())

        # Top N selector
        top_n = st.slider("Top N shows", 5, 40, 20, key="show_top_n")

        # Show-level grouped bar: Events vs Stacked Users
        st.plotly_chart(
            show_grouped_bar_chart(show_agg, top_n),
            use_container_width=True,
        )

        # Genre donut side by side
        if "genre" in content_df.columns:
            genre_agg = content_df.groupby("genre", as_index=False).agg({
                "eventCount": "sum",
                "totalUsers": "sum",
            }).sort_values("eventCount", ascending=False)

            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.plotly_chart(
                    donut_chart(genre_agg, "genre", "eventCount", "Events by Genre"),
                    use_container_width=True,
                )
            with col_g2:
                st.plotly_chart(
                    donut_chart(genre_agg, "genre", "totalUsers", "Users by Genre"),
                    use_container_width=True,
                )

        st.divider()

        # ─── DRILL DOWN: Select a show to see episodes ───
        st.markdown("### 🔍 Drill Down — Episode View")
        show_list = show_agg["show_name"].tolist()
        selected_show = st.selectbox(
            "Select a show to view episodes",
            options=show_list,
            index=0,
            key="drilldown_show",
        )

        if selected_show:
            st.plotly_chart(
                episode_drilldown_chart(content_df, selected_show),
                use_container_width=True,
            )

            # Episode data table for the selected show
            show_episodes = content_df[content_df["show_name"] == selected_show].copy()
            if "ep_no" in show_episodes.columns:
                show_episodes["ep_no_num"] = pd.to_numeric(show_episodes["ep_no"], errors="coerce").fillna(0)
                show_episodes = show_episodes.sort_values("ep_no_num")
                show_episodes = show_episodes.drop(columns=["ep_no_num"])

            display_cols = {
                "content_title": "Episode Name",
                "ep_no": "Ep #",
                "eventCount": "Events",
                "totalUsers": "Distinct Users",
                "activeUsers": "Active Users",
                "newUsers": "New Users",
                "genre": "Genre",
            }
            display_ep = show_episodes.rename(
                columns={k: v for k, v in display_cols.items() if k in show_episodes.columns}
            )
            st.dataframe(
                display_ep,
                use_container_width=True,
                height=min(400, max(200, len(show_episodes) * 40)),
                column_config={
                    "Events": st.column_config.NumberColumn(format="%d"),
                    "Distinct Users": st.column_config.NumberColumn(format="%d"),
                    "Active Users": st.column_config.NumberColumn(format="%d"),
                    "New Users": st.column_config.NumberColumn(format="%d"),
                },
            )

        st.divider()

        # Full data download
        csv = content_df.to_csv(index=False)
        st.download_button(
            "📥 Download Full Content Data (CSV)",
            csv,
            "hoichoi_content_data.csv",
            "text/csv",
            use_container_width=True,
        )

    else:
        st.warning("No content data found for the selected filters.")

except Exception as e:
    st.error(f"Error loading content analytics: {e}")


# ═══════════════════════════════════════════════
# SECTION 3: GEOGRAPHY (collapsed by default)
# ═══════════════════════════════════════════════
st.divider()
with st.expander("🌍 Geography Breakdown", expanded=False):
    try:
        country_df = fetch_by_country(start_str, end_str, content_filter)

        if not country_df.empty:
            geo_metric = st.selectbox(
                "Metric",
                ["eventCount", "totalUsers", "activeUsers", "newUsers"],
                format_func=lambda x: {
                    "eventCount": "Total Events",
                    "totalUsers": "Distinct Users",
                    "newUsers": "New Users",
                    "activeUsers": "Active Users",
                }[x],
                key="geo_metric",
            )

            st.plotly_chart(
                country_choropleth(country_df, geo_metric),
                use_container_width=True,
            )

            col_bar, col_donut = st.columns([3, 2])
            with col_bar:
                st.plotly_chart(
                    country_bar_chart(country_df, geo_metric),
                    use_container_width=True,
                )
            with col_donut:
                st.plotly_chart(
                    donut_chart(
                        country_df.head(8), "country", geo_metric,
                        f"Share by Country ({geo_metric})",
                    ),
                    use_container_width=True,
                )

            csv = country_df.to_csv(index=False)
            st.download_button(
                "📥 Download Geography Data (CSV)",
                csv,
                "hoichoi_geography_data.csv",
                "text/csv",
                use_container_width=True,
            )
        else:
            st.warning("No geography data found.")

    except Exception as e:
        st.error(f"Error loading geography: {e}")


# ═══════════════════════════════════════════════
# SECTION 4: CHATBOT (collapsed by default)
# ═══════════════════════════════════════════════
st.divider()
with st.expander("💬 Ask the Data", expanded=False):
    st.markdown(
        "Ask questions about your Hoichoi audio listening data. "
        "The AI analyst has access to all the dashboard data."
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    try:
        chat_summary = fetch_summary_metrics(start_str, end_str, content_filter, country_filter)
        chat_daily = fetch_daily_trend(start_str, end_str, content_filter, country_filter)
        chat_content = fetch_by_content(start_str, end_str, country_filter)
        chat_content = enrich_with_metadata(chat_content, metadata_df)
        chat_country = fetch_by_country(start_str, end_str, content_filter)
        data_context = prepare_chatbot_context(
            chat_summary, chat_daily, chat_content, chat_country
        )
    except Exception:
        data_context = "Error loading data context."

    with st.container():
        suggestions = get_suggested_questions()
        cols = st.columns(2)
        for i, q in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(q, key=f"suggest_{i}", use_container_width=True):
                    st.session_state.pending_question = q

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask a question about your listening data...")

    if hasattr(st.session_state, "pending_question") and st.session_state.pending_question:
        prompt = st.session_state.pending_question
        st.session_state.pending_question = None

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing data..."):
                response = get_chatbot_response(
                    prompt, data_context, st.session_state.chat_history[:-1]
                )
                st.markdown(response)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": response}
        )

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
