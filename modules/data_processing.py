"""
Data fetching and processing layer.
All functions use Streamlit caching for performance.
"""

import streamlit as st
import pandas as pd
from modules.ga4_client import run_report
from modules.constants import DATA_CACHE_TTL, FILTER_CACHE_TTL


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner="Fetching summary metrics...")
def fetch_summary_metrics(
    start_date: str,
    end_date: str,
    content_titles: tuple | None = None,
    countries: tuple | None = None,
) -> dict:
    """Fetch top-line KPIs for the Listened_ event."""
    df = run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["date"],
        metrics=["eventCount", "totalUsers", "newUsers", "activeUsers"],
        content_titles=list(content_titles) if content_titles else None,
        countries=list(countries) if countries else None,
    )

    if df.empty:
        return {
            "total_events": 0,
            "total_users": 0,
            "new_users": 0,
            "active_users": 0,
            "days": 0,
            "avg_events_per_day": 0,
        }

    return {
        "total_events": int(df["eventCount"].sum()),
        "total_users": int(df["totalUsers"].sum()),
        "new_users": int(df["newUsers"].sum()),
        "active_users": int(df["activeUsers"].sum()),
        "days": len(df),
        "avg_events_per_day": int(df["eventCount"].sum() / max(len(df), 1)),
    }


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner="Fetching daily trend...")
def fetch_daily_trend(
    start_date: str,
    end_date: str,
    content_titles: tuple | None = None,
    countries: tuple | None = None,
) -> pd.DataFrame:
    """Daily breakdown of Listened_ events."""
    return run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["date"],
        metrics=["eventCount", "totalUsers", "newUsers", "activeUsers"],
        content_titles=list(content_titles) if content_titles else None,
        countries=list(countries) if countries else None,
    )


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner="Fetching content data...")
def fetch_by_content(
    start_date: str,
    end_date: str,
    countries: tuple | None = None,
) -> pd.DataFrame:
    """Content-wise breakdown of Listened_ events."""
    df = run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["customEvent:content_title"],
        metrics=["eventCount", "totalUsers", "newUsers", "activeUsers"],
        countries=list(countries) if countries else None,
    )

    if not df.empty:
        df = df.sort_values("eventCount", ascending=False).reset_index(drop=True)
        df["events_per_user"] = (df["eventCount"] / df["activeUsers"].replace(0, 1)).round(2)

    return df


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner="Fetching content x date data...")
def fetch_content_by_date(
    start_date: str,
    end_date: str,
    content_titles: tuple | None = None,
    countries: tuple | None = None,
) -> pd.DataFrame:
    """Content x Date breakdown."""
    return run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["customEvent:content_title", "date"],
        metrics=["eventCount", "totalUsers", "newUsers", "activeUsers"],
        content_titles=list(content_titles) if content_titles else None,
        countries=list(countries) if countries else None,
    )


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner="Fetching geography data...")
def fetch_by_country(
    start_date: str,
    end_date: str,
    content_titles: tuple | None = None,
) -> pd.DataFrame:
    """Country-wise breakdown of Listened_ events."""
    df = run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["country"],
        metrics=["eventCount", "totalUsers", "newUsers", "activeUsers"],
        content_titles=list(content_titles) if content_titles else None,
    )

    if not df.empty:
        total = df["eventCount"].sum()
        df = df.sort_values("eventCount", ascending=False).reset_index(drop=True)
        df["pct_share"] = (df["eventCount"] / total * 100).round(1)

    return df


@st.cache_data(ttl=DATA_CACHE_TTL, show_spinner="Fetching content x geography...")
def fetch_content_by_country(
    start_date: str,
    end_date: str,
    content_titles: tuple | None = None,
    countries: tuple | None = None,
) -> pd.DataFrame:
    """Content x Country breakdown."""
    return run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["customEvent:content_title", "country"],
        metrics=["eventCount", "totalUsers", "newUsers", "activeUsers"],
        content_titles=list(content_titles) if content_titles else None,
        countries=list(countries) if countries else None,
    )


@st.cache_data(ttl=FILTER_CACHE_TTL, show_spinner="Loading filter options...")
def get_filter_options(start_date: str, end_date: str) -> tuple[list[str], list[str]]:
    """Fetch distinct content titles and countries for filter dropdowns."""
    # Get content titles
    content_df = run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["customEvent:content_title"],
        metrics=["eventCount"],
    )
    content_titles = (
        content_df.sort_values("eventCount", ascending=False)["content_title"].tolist()
        if not content_df.empty
        else []
    )

    # Get countries
    country_df = run_report(
        start_date=start_date,
        end_date=end_date,
        dimensions=["country"],
        metrics=["eventCount"],
    )
    countries = (
        country_df.sort_values("eventCount", ascending=False)["country"].tolist()
        if not country_df.empty
        else []
    )

    return content_titles, countries


def prepare_chatbot_context(
    summary: dict,
    daily_df: pd.DataFrame,
    content_df: pd.DataFrame,
    country_df: pd.DataFrame,
) -> str:
    """Serialize dashboard data into text for the chatbot."""
    ctx = []
    ctx.append("=== HOICHOI AUDIO DASHBOARD DATA ===\n")

    # KPIs
    ctx.append(f"SUMMARY METRICS:")
    ctx.append(f"  Total Listen Events: {summary['total_events']:,}")
    ctx.append(f"  Distinct Users: {summary['total_users']:,}")
    ctx.append(f"  New Users: {summary['new_users']:,}")
    ctx.append(f"  Active Users: {summary['active_users']:,}")
    ctx.append(f"  Days in Period: {summary['days']}")
    ctx.append(f"  Avg Events/Day: {summary['avg_events_per_day']:,}")
    ctx.append("")

    # Daily trend
    if not daily_df.empty:
        ctx.append("DAILY TREND (date | events | users | new | active):")
        for _, row in daily_df.iterrows():
            d = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])
            ctx.append(
                f"  {d} | {row['eventCount']:,} | {row['totalUsers']:,} | "
                f"{row['newUsers']:,} | {row['activeUsers']:,}"
            )
        ctx.append("")

    # Top content
    if not content_df.empty:
        ctx.append(f"TOP CONTENT (showing top 30 of {len(content_df)}):")
        ctx.append("  content_title | events | users | new_users | active_users")
        for _, row in content_df.head(30).iterrows():
            ctx.append(
                f"  {row['content_title']} | {row['eventCount']:,} | "
                f"{row['totalUsers']:,} | {row['newUsers']:,} | {row['activeUsers']:,}"
            )
        ctx.append("")

    # Geography
    if not country_df.empty:
        ctx.append("GEOGRAPHY:")
        for _, row in country_df.iterrows():
            ctx.append(
                f"  {row['country']} | {row['eventCount']:,} events | "
                f"{row.get('pct_share', 0):.1f}% share"
            )

    return "\n".join(ctx)
