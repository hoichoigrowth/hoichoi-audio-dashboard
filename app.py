"""
Hoichoi Audio Analytics Dashboard
Streamlit app for Listened_ event analysis from Google Analytics 4.
Enriched with audio metadata from Google Sheets (show name, genre).
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
    dual_axis_users_chart,
    top_content_bar_chart,
    country_bar_chart,
    country_choropleth,
    content_trend_chart,
    donut_chart,
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


# ─── Load Audio Metadata (cached) ───
metadata_df = fetch_audio_metadata()

# Extract filter options from metadata
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

    # ─── Show Name filter (from Google Sheets) ───
    st.markdown("### 📺 Show Filter")
    selected_shows = st.multiselect(
        "Select shows",
        options=show_name_options,
        default=[],
        placeholder="All shows",
    )

    # ─── Genre filter (from Google Sheets) ───
    st.markdown("### 🎭 Genre Filter")
    selected_genres = st.multiselect(
        "Select genres",
        options=genre_options,
        default=[],
        placeholder="All genres",
    )

    st.divider()

    # Fetch filter options from GA4
    try:
        content_options, country_options = get_filter_options(start_str, end_str)
    except Exception:
        content_options, country_options = [], []

    # Content filter
    st.markdown("### 🎵 Episode Filter")
    selected_content = st.multiselect(
        "Select episode titles",
        options=content_options,
        default=[],
        placeholder="All episodes",
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

    # Metadata status
    if not metadata_df.empty:
        st.success(f"📋 {len(metadata_df)} episodes mapped from Google Sheets")
    else:
        st.warning("⚠️ Could not load audio metadata")

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


# ─── Resolve show/genre filters into content_title list ───
def resolve_metadata_filters(
    selected_shows: list,
    selected_genres: list,
    selected_content: list,
    metadata: pd.DataFrame,
) -> list | None:
    """
    Combine show/genre/episode filters into a single content_title list.
    Returns None if no filters are active (= all content).
    """
    filtered_episodes = None

    if not metadata.empty and (selected_shows or selected_genres):
        mask = pd.Series(True, index=metadata.index)
        if selected_shows:
            mask &= metadata["show_name"].isin(selected_shows)
        if selected_genres:
            mask &= metadata["genre"].isin(selected_genres)
        filtered_episodes = metadata.loc[mask, "ep_name"].tolist()

    # Combine with directly selected episodes
    if selected_content:
        if filtered_episodes is not None:
            # Intersection: must match both metadata filter AND direct selection
            filtered_episodes = list(set(filtered_episodes) & set(selected_content))
        else:
            filtered_episodes = selected_content

    return filtered_episodes


resolved_content = resolve_metadata_filters(
    selected_shows, selected_genres, selected_content, metadata_df
)

# ─── Convert filters to tuples for caching ───
content_filter = tuple(resolved_content) if resolved_content else None
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

        # Daily Trend — two charts side by side
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


# ═══════════════════════════════════════
# TAB 2: CONTENT ANALYSIS
# ═══════════════════════════════════════
with tab_content:
    try:
        content_df = fetch_by_content(start_str, end_str, country_filter)

        # Enrich with metadata
        content_df = enrich_with_metadata(content_df, metadata_df)

        # Apply show/genre filters if metadata columns exist
        if not content_df.empty:
            if selected_shows and "show_name" in content_df.columns:
                content_df = content_df[content_df["show_name"].isin(selected_shows)]
            if selected_genres and "genre" in content_df.columns:
                content_df = content_df[content_df["genre"].isin(selected_genres)]

        if not content_df.empty:
            st.markdown(f"### 📊 {len(content_df)} Content Titles Found")

            # Show/Genre summary if available
            if "show_name" in content_df.columns:
                shows_count = content_df["show_name"].nunique()
                genres_count = content_df["genre"].nunique() if "genre" in content_df.columns else 0
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.metric("Unique Shows", shows_count)
                with sc2:
                    st.metric("Unique Genres", genres_count)

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

            # ─── Show-wise aggregation ───
            if "show_name" in content_df.columns:
                st.markdown("### 📺 Show-wise Breakdown")
                show_agg = content_df.groupby("show_name", as_index=False).agg({
                    "eventCount": "sum",
                    "totalUsers": "sum",
                    "activeUsers": "sum",
                    "newUsers": "sum",
                }).sort_values("eventCount", ascending=False)
                show_agg["events_per_user"] = (show_agg["eventCount"] / show_agg["activeUsers"].replace(0, 1)).round(2)

                col_show_chart, col_show_donut = st.columns([3, 2])
                with col_show_chart:
                    st.plotly_chart(
                        top_content_bar_chart(
                            show_agg.rename(columns={"show_name": "content_title"}),
                            content_metric, min(top_n, len(show_agg))
                        ),
                        use_container_width=True,
                    )
                with col_show_donut:
                    st.plotly_chart(
                        donut_chart(
                            show_agg.head(10).rename(columns={"show_name": "content_title"}),
                            "content_title", content_metric,
                            f"Top Shows by {content_metric}",
                        ),
                        use_container_width=True,
                    )

                st.divider()

            # ─── Genre-wise aggregation ───
            if "genre" in content_df.columns:
                st.markdown("### 🎭 Genre-wise Breakdown")
                genre_agg = content_df.groupby("genre", as_index=False).agg({
                    "eventCount": "sum",
                    "totalUsers": "sum",
                    "activeUsers": "sum",
                    "newUsers": "sum",
                }).sort_values("eventCount", ascending=False)

                col_genre_bar, col_genre_donut = st.columns([3, 2])
                with col_genre_bar:
                    st.plotly_chart(
                        top_content_bar_chart(
                            genre_agg.rename(columns={"genre": "content_title"}),
                            content_metric, len(genre_agg)
                        ),
                        use_container_width=True,
                    )
                with col_genre_donut:
                    st.plotly_chart(
                        donut_chart(
                            genre_agg.rename(columns={"genre": "content_title"}),
                            "content_title", content_metric,
                            f"Genre Share by {content_metric}",
                        ),
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
            table_cols = {
                "content_title": "Content Title",
                "eventCount": "Events",
                "totalUsers": "Distinct Users",
                "newUsers": "New Users",
                "activeUsers": "Active Users",
                "events_per_user": "Events/User",
            }
            if "show_name" in content_df.columns:
                table_cols["show_name"] = "Show Name"
            if "genre" in content_df.columns:
                table_cols["genre"] = "Genre"
            if "ep_no" in content_df.columns:
                table_cols["ep_no"] = "Episode #"

            display_df = content_df.rename(columns=table_cols)
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
                # Enrich with metadata
                content_country_df = enrich_with_metadata(content_country_df, metadata_df)
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
        st.info("This shows every content title x date combination with full metrics, enriched with show & genre.")

        detail_df = fetch_content_by_date(
            start_str, end_str, content_filter, country_filter
        )

        if not detail_df.empty:
            # Enrich with metadata
            detail_df = enrich_with_metadata(detail_df, metadata_df)

            # Apply show/genre filters
            if selected_shows and "show_name" in detail_df.columns:
                detail_df = detail_df[detail_df["show_name"].isin(selected_shows)]
            if selected_genres and "genre" in detail_df.columns:
                detail_df = detail_df[detail_df["genre"].isin(selected_genres)]

            # Add computed columns
            detail_df["events_per_user"] = (
                detail_df["eventCount"] / detail_df["activeUsers"].replace(0, 1)
            ).round(2)

            # Summary stats
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Total Rows", f"{len(detail_df):,}")
            with c2:
                st.metric("Unique Episodes", f"{detail_df['content_title'].nunique():,}")
            with c3:
                shows = detail_df["show_name"].nunique() if "show_name" in detail_df.columns else "N/A"
                st.metric("Unique Shows", shows)
            with c4:
                st.metric("Date Range", f"{detail_df['date'].min().strftime('%b %d')} - {detail_df['date'].max().strftime('%b %d')}")

            st.divider()

            # Display
            detail_rename = {
                "content_title": "Episode",
                "date": "Date",
                "eventCount": "Events",
                "totalUsers": "Distinct Users",
                "newUsers": "New Users",
                "activeUsers": "Active Users",
                "events_per_user": "Events/User",
            }
            if "show_name" in detail_df.columns:
                detail_rename["show_name"] = "Show Name"
            if "genre" in detail_df.columns:
                detail_rename["genre"] = "Genre"
            if "ep_no" in detail_df.columns:
                detail_rename["ep_no"] = "Episode #"

            display_detail = detail_df.rename(columns=detail_rename)

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
        chat_content = enrich_with_metadata(chat_content, metadata_df)
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
