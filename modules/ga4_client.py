"""
Google Analytics 4 API client for Hoichoi Audio Dashboard.
Handles authentication, report execution, and data conversion.
"""

import streamlit as st
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
    FilterExpression,
    Filter,
    OrderBy,
)
from google.oauth2 import service_account

from modules.constants import EVENT_NAME


def get_ga4_client() -> BetaAnalyticsDataClient:
    """Create authenticated GA4 client using Streamlit secrets."""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        return BetaAnalyticsDataClient(credentials=credentials)
    except Exception as e:
        st.error(f"Failed to authenticate with GA4: {e}")
        st.info(
            "Please configure `gcp_service_account` in `.streamlit/secrets.toml` "
            "or Streamlit Cloud secrets."
        )
        st.stop()


def get_property_id() -> str:
    """Get GA4 property ID from Streamlit secrets."""
    try:
        return st.secrets["GA4_PROPERTY_ID"]
    except Exception:
        st.error("GA4_PROPERTY_ID not found in secrets.")
        st.info("Add `GA4_PROPERTY_ID = 'properties/XXXXXXX'` to your secrets.")
        st.stop()


def _build_listened_filter(
    content_titles: list[str] | None = None,
    countries: list[str] | None = None,
) -> FilterExpression:
    """
    Build GA4 filter expression.
    Always includes eventName == 'Listened_'.
    Optionally adds content_title and country filters.
    """
    # Base filter: eventName == Listened_
    event_filter = FilterExpression(
        filter=Filter(
            field_name="eventName",
            string_filter=Filter.StringFilter(
                value=EVENT_NAME,
                match_type=Filter.StringFilter.MatchType.EXACT,
            ),
        )
    )

    filters = [event_filter]

    # Content title filter (IN list)
    if content_titles and len(content_titles) > 0:
        content_filter = FilterExpression(
            filter=Filter(
                field_name="customEvent:content_title",
                in_list_filter=Filter.InListFilter(values=content_titles),
            )
        )
        filters.append(content_filter)

    # Country filter (IN list)
    if countries and len(countries) > 0:
        country_filter = FilterExpression(
            filter=Filter(
                field_name="country",
                in_list_filter=Filter.InListFilter(values=countries),
            )
        )
        filters.append(country_filter)

    # Combine with AND
    if len(filters) == 1:
        return filters[0]

    return FilterExpression(
        and_group=FilterExpression.AndGroup(expressions=filters)
    )


def run_report(
    start_date: str,
    end_date: str,
    dimensions: list[str],
    metrics: list[str],
    content_titles: list[str] | None = None,
    countries: list[str] | None = None,
    limit: int = 10000,
) -> pd.DataFrame:
    """
    Execute a GA4 RunReportRequest and return results as a DataFrame.
    Handles pagination for large result sets.

    Args:
        start_date: YYYY-MM-DD format
        end_date: YYYY-MM-DD format
        dimensions: List of dimension names (e.g., ['date', 'customEvent:content_title'])
        metrics: List of metric names (e.g., ['eventCount', 'totalUsers'])
        content_titles: Optional list of content titles to filter by
        countries: Optional list of countries to filter by
        limit: Max rows per request (GA4 max is 10000)

    Returns:
        pandas DataFrame with dimension and metric columns
    """
    client = get_ga4_client()
    property_id = get_property_id()

    dimension_filter = _build_listened_filter(content_titles, countries)

    all_rows = []
    offset = 0

    while True:
        request = RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            dimension_filter=dimension_filter,
            limit=limit,
            offset=offset,
        )

        response = client.run_report(request)

        for row in response.rows:
            row_data = {}
            for i, dim in enumerate(dimensions):
                col_name = dim.replace("customEvent:", "")
                row_data[col_name] = row.dimension_values[i].value
            for i, met in enumerate(metrics):
                row_data[met] = int(row.metric_values[i].value)
            all_rows.append(row_data)

        # Check if there are more pages
        if len(response.rows) < limit:
            break
        offset += limit

    df = pd.DataFrame(all_rows)

    # Convert date column if present
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        df = df.sort_values("date")

    return df
