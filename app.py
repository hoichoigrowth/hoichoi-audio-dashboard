"""
Hoichoi Audio Analytics Dashboard
Single-page, fully reactive Streamlit dashboard for Listened_ event analysis.
Click on a show bar to drill down into episodes; all charts react.
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
    top_content_bar_chart_generic,
)
from modules.chatbot import get_chatbot_response, get_suggested_questions
from modules.constants import COLORS
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
    .main-title { font-size: 2rem; font-weight: 700; color: #6C3483; margin-bottom: 0; }
    .sub-title { font-size: 1rem; color: #888; margin-top: -10px; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    .selected-show { font-size: 1.3rem; font-weight: 600; color: #2ECC71; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Session State ───
if "selected_show" not in st.session_state:
    st.session_state.selected_show = None

# ─── Load Metadata ───
metadata_df = fetch_audio_metadata()
show_name_options = sorted(metadata_df["show_name"].dropna().unique().tolist()) if not metadata_df.empty and "show_name" in metadata_df.columns else []
genre_options = sorted(metadata_df["genre"].dropna().unique().tolist()) if not metadata_df.empty and "genre" in metadata_df.columns else []

# ─── Sidebar ───
with st.sidebar:
    st.markdown("**🎧 Hoichoi Audio** · Listened_ Dashboard")

    default_end = datetime.now().date()
    default_start = default_end - timedelta(days=30)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start", value=default_start)
    with col2:
        end_date = st.date_input("End", value=default_end)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    selected_shows = st.multiselect("📺 Show", options=show_name_options, default=[], placeholder="All shows")
    selected_genres = st.multiselect("🎭 Genre", options=genre_options, default=[], placeholder="All genres")
    selected_countries = st.multiselect("🌍 Country", options=st.session_state.get("country_options", []), default=[], placeholder="All countries")

    if st.session_state.selected_show:
        st.info(f"📺 Drilled into: **{st.session_state.selected_show}**")
        if st.button("✕ Clear Selection", use_container_width=True):
            st.session_state.selected_show = None
            st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.session_state.selected_show = None
            st.session_state.geo_loaded = False
            st.rerun()
    with c2:
        if not metadata_df.empty:
            st.caption(f"📋 {len(metadata_df)} eps")


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

# If a show is selected via click, further filter to that show's episodes
active_show = st.session_state.selected_show
if active_show and not metadata_df.empty and "show_name" in metadata_df.columns:
    show_episodes = metadata_df[metadata_df["show_name"] == active_show]["ep_name"].tolist()
    if show_episodes:
        # Intersect with existing filter if any
        if content_filter:
            show_episodes = list(set(show_episodes) & set(content_filter))
        content_filter_for_overview = tuple(show_episodes) if show_episodes else content_filter
    else:
        content_filter_for_overview = content_filter
else:
    content_filter_for_overview = content_filter


# ═══════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════
st.markdown('<p class="main-title">🎧 Hoichoi Audio Analytics</p>', unsafe_allow_html=True)
subtitle = f'Listened_ Event Dashboard | {start_str} to {end_str}'
if active_show:
    subtitle += f' | 📺 {active_show}'
st.markdown(f'<p class="sub-title">{subtitle}</p>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════
# SECTION 1: OVERVIEW KPIs + DAILY CHARTS
# (Reactive: filters to selected show if clicked)
# ═══════════════════════════════════════════════
try:
    summary = fetch_summary_metrics(start_str, end_str, content_filter_for_overview, country_filter)
    daily_df = fetch_daily_trend(start_str, end_str, content_filter_for_overview, country_filter)

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
# SECTION 2: CONTENT ANALYTICS
# Show-level with click-to-drill-down
# ═══════════════════════════════════════════════
st.divider()

try:
    content_df = fetch_by_content(start_str, end_str, country_filter)
    content_df = enrich_with_metadata(content_df, metadata_df)

    if not content_df.empty:
        if selected_shows and "show_name" in content_df.columns:
            content_df = content_df[content_df["show_name"].isin(selected_shows)]
        if selected_genres and "genre" in content_df.columns:
            content_df = content_df[content_df["genre"].isin(selected_genres)]

    if not content_df.empty and "show_name" in content_df.columns:

        # ─── Content Analytics header ───
        st.markdown("## 📺 Content Analytics")

        # Genre filter options
        chart_genre_options = sorted(content_df["genre"].dropna().unique().tolist()) if "genre" in content_df.columns else []
        has_primary_genre = "primary_genre" in content_df.columns
        primary_genre_options = sorted(content_df["primary_genre"].dropna().unique().tolist()) if has_primary_genre else []
        chart_df = content_df.copy()

        # ─── If NO show selected: show the show-level view ───
        if not active_show:
            st.caption("👆 Click on a show bar to drill down into its episodes")

            # ─── Persistent filters: inline ───
            fc1, fc2, fc3, fc4 = st.columns([1, 1, 1, 1])
            with fc1:
                top_n = st.slider("Top N shows", 5, 40, 20, key="show_top_n")
            with fc2:
                chart_metric_mode = st.selectbox(
                    "📊 Metric",
                    options=["both", "event_count", "unique_users"],
                    format_func=lambda x: {
                        "both": "Events + Users",
                        "event_count": "Event Count",
                        "unique_users": "Unique Users",
                    }[x],
                    index=0,
                    key="chart_metric_mode",
                )
            with fc3:
                chart_genre_filter = st.multiselect(
                    "🎭 Genre",
                    options=chart_genre_options,
                    default=[],
                    placeholder="All genres",
                    key="chart_genre_filter",
                )
            with fc4:
                chart_primary_genre_filter = st.multiselect(
                    "🏷️ Primary Genre",
                    options=primary_genre_options,
                    default=[],
                    placeholder="All primary genres",
                    key="chart_primary_genre_filter",
                ) if has_primary_genre else []

            # Apply filters
            if chart_genre_filter and "genre" in chart_df.columns:
                chart_df = chart_df[chart_df["genre"].isin(chart_genre_filter)]
            if chart_primary_genre_filter and has_primary_genre:
                chart_df = chart_df[chart_df["primary_genre"].isin(chart_primary_genre_filter)]

            # Show KPIs
            show_agg = chart_df.groupby("show_name", as_index=False).agg({
                "eventCount": "sum",
                "totalUsers": "sum",
                "activeUsers": "sum",
                "newUsers": "sum",
            }).sort_values("eventCount", ascending=False)

            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric("Total Shows", show_agg["show_name"].nunique())
            with sc2:
                st.metric("Total Episodes", len(chart_df))
            with sc3:
                if "genre" in chart_df.columns:
                    st.metric("Genres", chart_df["genre"].nunique())

            # ─── Primary Genre bar chart ───
            if has_primary_genre and not chart_primary_genre_filter:
                pg_agg = chart_df.groupby("primary_genre", as_index=False).agg({
                    "eventCount": "sum",
                    "totalUsers": "sum",
                }).sort_values("eventCount", ascending=False)

                if not pg_agg.empty:
                    col_pg1, col_pg2 = st.columns(2)
                    with col_pg1:
                        st.plotly_chart(
                            top_content_bar_chart_generic(
                                pg_agg, "primary_genre", "eventCount", "Events by Primary Genre", top_n=15
                            ),
                            use_container_width=True,
                        )
                    with col_pg2:
                        st.plotly_chart(
                            top_content_bar_chart_generic(
                                pg_agg, "primary_genre", "totalUsers", "Users by Primary Genre", top_n=15
                            ),
                            use_container_width=True,
                        )

            # Show bar chart with click selection
            show_chart = show_grouped_bar_chart(show_agg, top_n, metric_mode=chart_metric_mode)
            event = st.plotly_chart(
                show_chart,
                use_container_width=True,
                on_select="rerun",
                key="show_bar_click",
            )

            # Handle click: extract show name from selection
            if event and event.selection and event.selection.points:
                clicked_point = event.selection.points[0]
                clicked_show = clicked_point.get("y", None)
                if clicked_show and clicked_show in show_agg["show_name"].values:
                    st.session_state.selected_show = clicked_show
                    st.rerun()

            # Genre donuts
            if "genre" in chart_df.columns and not chart_genre_filter:
                genre_agg = chart_df.groupby("genre", as_index=False).agg({
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

        # ─── If show IS selected: episode drill-down ───
        else:
            st.markdown(f"### 📺 {active_show} — Episode Breakdown")

            # ─── Persistent filters for drill-down ───
            dc1, dc2, dc3 = st.columns([2, 2, 2])
            with dc1:
                if st.button("⬅️ Back to All Shows", type="primary", use_container_width=True):
                    st.session_state.selected_show = None
                    st.rerun()
            with dc2:
                chart_metric_mode = st.selectbox(
                    "📊 Metric",
                    options=["both", "event_count", "unique_users"],
                    format_func=lambda x: {
                        "both": "Events + Users",
                        "event_count": "Event Count",
                        "unique_users": "Unique Users",
                    }[x],
                    index=0,
                    key="chart_metric_mode",
                )
            with dc3:
                chart_genre_filter = st.multiselect(
                    "🎭 Genre",
                    options=chart_genre_options,
                    default=[],
                    placeholder="All genres",
                    key="chart_genre_filter",
                )

            if chart_genre_filter and "genre" in chart_df.columns:
                chart_df = chart_df[chart_df["genre"].isin(chart_genre_filter)]

            # Episode drilldown chart (with same metric mode)
            st.plotly_chart(
                episode_drilldown_chart(chart_df, active_show, metric_mode=chart_metric_mode),
                use_container_width=True,
            )

            # Episode data table
            show_episodes_df = chart_df[chart_df["show_name"] == active_show].copy()
            if "ep_no" in show_episodes_df.columns:
                show_episodes_df["ep_no_num"] = pd.to_numeric(show_episodes_df["ep_no"], errors="coerce").fillna(0)
                show_episodes_df = show_episodes_df.sort_values("ep_no_num", ascending=True)
                show_episodes_df = show_episodes_df.drop(columns=["ep_no_num"])

            # Episode KPIs
            ec1, ec2, ec3, ec4 = st.columns(4)
            with ec1:
                st.metric("Episodes", len(show_episodes_df))
            with ec2:
                st.metric("Total Events", f"{show_episodes_df['eventCount'].sum():,}")
            with ec3:
                st.metric("Distinct Users", f"{show_episodes_df['totalUsers'].sum():,}")
            with ec4:
                genre_val = show_episodes_df["genre"].iloc[0] if "genre" in show_episodes_df.columns and len(show_episodes_df) > 0 else "N/A"
                st.metric("Genre", genre_val)

            display_cols = {
                "content_title": "Episode Name",
                "ep_no": "Ep #",
                "eventCount": "Events",
                "totalUsers": "Distinct Users",
                "activeUsers": "Active Users",
                "newUsers": "New Users",
            }
            display_ep = show_episodes_df.rename(
                columns={k: v for k, v in display_cols.items() if k in show_episodes_df.columns}
            )
            st.dataframe(
                display_ep,
                use_container_width=True,
                height=min(500, max(200, len(show_episodes_df) * 40)),
                column_config={
                    "Events": st.column_config.NumberColumn(format="%d"),
                    "Distinct Users": st.column_config.NumberColumn(format="%d"),
                    "Active Users": st.column_config.NumberColumn(format="%d"),
                    "New Users": st.column_config.NumberColumn(format="%d"),
                },
            )

        st.divider()

        # Download (always available)
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
# SECTION 3: GEOGRAPHY (collapsed)
# ═══════════════════════════════════════════════
st.divider()

# Lazy-load geography: only fetch when user clicks button
if "geo_loaded" not in st.session_state:
    st.session_state.geo_loaded = False

with st.expander("🌍 Geography Breakdown", expanded=st.session_state.geo_loaded):
    if not st.session_state.geo_loaded:
        if st.button("📊 Load Geography Data", use_container_width=True, key="load_geo"):
            st.session_state.geo_loaded = True
            st.rerun()
        st.caption("Click above to load geography data (saves load time)")
    else:
        try:
            country_df = fetch_by_country(start_str, end_str, content_filter_for_overview)

            # Populate sidebar country filter for next rerun
            if not country_df.empty:
                st.session_state.country_options = country_df["country"].tolist()

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

                st.plotly_chart(country_choropleth(country_df, geo_metric), use_container_width=True)

                col_bar, col_donut = st.columns([3, 2])
                with col_bar:
                    st.plotly_chart(country_bar_chart(country_df, geo_metric), use_container_width=True)
                with col_donut:
                    st.plotly_chart(
                        donut_chart(country_df.head(8), "country", geo_metric, f"Share by Country ({geo_metric})"),
                        use_container_width=True,
                    )

                csv = country_df.to_csv(index=False)
                st.download_button("📥 Download Geography Data (CSV)", csv, "hoichoi_geography_data.csv", "text/csv", use_container_width=True)
            else:
                st.warning("No geography data found.")
        except Exception as e:
            st.error(f"Error loading geography: {e}")


# ═══════════════════════════════════════════════
# SECTION 4: CHATBOT (collapsed)
# ═══════════════════════════════════════════════
st.divider()
with st.expander("💬 Ask the Data", expanded=False):
    st.markdown("Ask questions about your Hoichoi audio listening data.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

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
                # Lazy-load chatbot context only when user actually asks
                try:
                    chat_summary = fetch_summary_metrics(start_str, end_str, content_filter, country_filter)
                    chat_daily = fetch_daily_trend(start_str, end_str, content_filter, country_filter)
                    chat_content = fetch_by_content(start_str, end_str, country_filter)
                    chat_content = enrich_with_metadata(chat_content, metadata_df)
                    chat_country = fetch_by_country(start_str, end_str, content_filter)
                    data_context = prepare_chatbot_context(chat_summary, chat_daily, chat_content, chat_country)
                except Exception:
                    data_context = "Error loading data context."
                response = get_chatbot_response(prompt, data_context, st.session_state.chat_history[:-1])
                st.markdown(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
