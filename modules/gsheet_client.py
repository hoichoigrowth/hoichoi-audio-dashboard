"""
Google Sheets client for fetching audio metadata.
Maps episode names to show names and genres.
"""

import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account

# Sheet config
SPREADSHEET_ID = "1kLomx3uFCnns8CKO4U1x2n4u7NxuHezUzu-doSI8GRs"
WORKSHEET_NAME = "Audio metadata"


def _get_gsheet_client() -> gspread.Client:
    """Create authenticated gspread client using the same service account."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return gspread.authorize(credentials)


@st.cache_data(ttl=14400, show_spinner="Loading audio metadata from Google Sheets...")
def fetch_audio_metadata() -> pd.DataFrame:
    """
    Fetch audio metadata from Google Sheets.
    Returns DataFrame with columns:
        show_name, ep_no, ep_name, genre
    """
    try:
        client = _get_gsheet_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        records = worksheet.get_all_records()

        df = pd.DataFrame(records)

        # Normalize column names
        col_mapping = {}
        for col in df.columns:
            col_lower = col.strip().lower()
            if "show" in col_lower and "name" in col_lower:
                col_mapping[col] = "show_name"
            elif col_lower in ("ep no.", "ep no", "ep_no", "episode no", "episode no."):
                col_mapping[col] = "ep_no"
            elif col_lower in ("ep. name", "ep name", "ep_name", "episode name", "episode_name"):
                col_mapping[col] = "ep_name"
            elif "genre" in col_lower:
                col_mapping[col] = "genre"

        df = df.rename(columns=col_mapping)

        # Keep only the columns we need
        keep_cols = [c for c in ["show_name", "ep_no", "ep_name", "genre"] if c in df.columns]
        df = df[keep_cols]

        # Clean up
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()

        # Drop empty rows
        if "ep_name" in df.columns:
            df = df[df["ep_name"].str.len() > 0]

        return df

    except Exception as e:
        st.warning(f"Could not load audio metadata from Google Sheets: {e}")
        return pd.DataFrame()


def enrich_with_metadata(ga_df: pd.DataFrame, metadata_df: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join GA4 data with audio metadata.
    Matches GA4 content_title to sheet's ep_name.
    """
    if metadata_df.empty or ga_df.empty:
        return ga_df

    if "content_title" not in ga_df.columns:
        return ga_df

    if "ep_name" not in metadata_df.columns:
        return ga_df

    # Merge on content_title == ep_name
    enriched = ga_df.merge(
        metadata_df,
        left_on="content_title",
        right_on="ep_name",
        how="left",
    )

    # Drop the duplicate ep_name column
    if "ep_name" in enriched.columns:
        enriched = enriched.drop(columns=["ep_name"])

    # Fill missing metadata
    if "show_name" in enriched.columns:
        enriched["show_name"] = enriched["show_name"].fillna("Unknown")
    if "genre" in enriched.columns:
        enriched["genre"] = enriched["genre"].fillna("Unknown")

    return enriched
