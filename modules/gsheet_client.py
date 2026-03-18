"""
Google Sheets client for fetching audio metadata.
Maps episode names to show names and genres.
Bulletproof: tries multiple auth strategies, retries, and detailed error logging.
"""

import streamlit as st
import pandas as pd
import traceback

# Sheet config
SPREADSHEET_ID = "1kLomx3uFCnns8CKO4U1x2n4u7NxuHezUzu-doSI8GRs"
WORKSHEET_NAME = "Sheet1"

# Public CSV export URL as ultimate fallback
GSHEET_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
    f"/gviz/tq?tqx=out:csv&sheet={WORKSHEET_NAME}"
)


def _get_service_account_info() -> dict:
    """Extract service account info from Streamlit secrets."""
    try:
        return dict(st.secrets["gcp_service_account"])
    except Exception:
        return {}


def _fetch_via_gspread(sa_info: dict) -> pd.DataFrame:
    """Primary method: use gspread with service account."""
    import gspread
    from google.oauth2 import service_account

    # Try multiple scope sets
    scope_options = [
        ["https://www.googleapis.com/auth/spreadsheets.readonly"],
        [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
        [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    ]

    last_err = None
    for scopes in scope_options:
        try:
            credentials = service_account.Credentials.from_service_account_info(
                sa_info, scopes=scopes
            )
            client = gspread.authorize(credentials)
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            records = worksheet.get_all_records()
            return pd.DataFrame(records)
        except Exception as e:
            last_err = e
            continue

    raise last_err or Exception("All gspread scope attempts failed")


def _fetch_via_csv() -> pd.DataFrame:
    """Fallback: fetch via public CSV export URL (sheet must be 'anyone with link')."""
    return pd.read_csv(GSHEET_CSV_URL)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to standard: show_name, ep_no, ep_name, genre, primary_genre."""
    col_mapping = {}
    for col in df.columns:
        cl = col.strip().lower()
        if "show" in cl and "name" in cl:
            col_mapping[col] = "show_name"
        elif cl in ("ep no.", "ep no", "ep_no", "episode no", "episode no.", "episode number"):
            col_mapping[col] = "ep_no"
        elif cl in ("ep. name", "ep name", "ep_name", "episode name", "episode_name"):
            col_mapping[col] = "ep_name"
        elif "primary" in cl and "genre" in cl:
            col_mapping[col] = "primary_genre"
        elif "genre" in cl:
            col_mapping[col] = "genre"

    df = df.rename(columns=col_mapping)

    # Keep only needed columns
    keep = [c for c in ["show_name", "ep_no", "ep_name", "genre", "primary_genre"] if c in df.columns]
    df = df[keep]

    # Clean strings
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    # Drop empty episode names
    if "ep_name" in df.columns:
        df = df[df["ep_name"].str.len() > 0]
        df = df[df["ep_name"] != "nan"]

    return df.reset_index(drop=True)


@st.cache_data(ttl=14400, show_spinner="Loading audio metadata from Google Sheets...")
def fetch_audio_metadata() -> pd.DataFrame:
    """
    Fetch audio metadata with multiple fallback strategies:
    1. gspread with service account (tries multiple scopes)
    2. Public CSV export URL
    Returns empty DataFrame only if everything fails.
    """
    errors = []

    # Strategy 1: gspread with service account
    sa_info = _get_service_account_info()
    if sa_info:
        try:
            df = _fetch_via_gspread(sa_info)
            df = _normalize_columns(df)
            if not df.empty:
                return df
        except Exception as e:
            errors.append(f"gspread: {e}")

    # Strategy 2: Public CSV fallback
    try:
        df = _fetch_via_csv()
        df = _normalize_columns(df)
        if not df.empty:
            return df
    except Exception as e:
        errors.append(f"CSV fallback: {e}")

    # All failed
    error_detail = " | ".join(errors) if errors else "No service account found in secrets"
    st.warning(f"Could not load audio metadata. Errors: {error_detail}")
    return pd.DataFrame()


def enrich_with_metadata(ga_df: pd.DataFrame, metadata_df: pd.DataFrame) -> pd.DataFrame:
    """
    Left-join GA4 data with audio metadata.
    Matches GA4 content_title to sheet's ep_name.
    Safe: returns original df if anything goes wrong.
    """
    if metadata_df.empty or ga_df.empty:
        return ga_df

    if "content_title" not in ga_df.columns:
        return ga_df

    if "ep_name" not in metadata_df.columns:
        return ga_df

    try:
        enriched = ga_df.merge(
            metadata_df,
            left_on="content_title",
            right_on="ep_name",
            how="left",
        )

        if "ep_name" in enriched.columns:
            enriched = enriched.drop(columns=["ep_name"])

        if "show_name" in enriched.columns:
            enriched["show_name"] = enriched["show_name"].fillna("Unknown")
        if "genre" in enriched.columns:
            enriched["genre"] = enriched["genre"].fillna("Unknown")
        if "primary_genre" in enriched.columns:
            enriched["primary_genre"] = enriched["primary_genre"].fillna("Unknown")

        return enriched

    except Exception:
        return ga_df
