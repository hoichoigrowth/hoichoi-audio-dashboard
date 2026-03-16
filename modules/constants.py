"""
Centralized configuration for Hoichoi Audio Analytics Dashboard.
"""

# GA4 Property - set via Streamlit secrets or env
# Format: "properties/XXXXXXX" (numeric property ID from GA4 Admin)
GA4_PROPERTY_ID = None  # Loaded from st.secrets at runtime

# Timezone & Currency
TIMEZONE = "Asia/Calcutta"
CURRENCY = "INR"

# Event to track
EVENT_NAME = "Listened_"

# ─── Dimensions ───
# Registered custom dimensions
REGISTERED_DIMENSIONS = {
    "content_title": "customEvent:content_title",
    "date": "date",
    "country": "country",
    "city": "city",
}

# NOT YET registered - show warning in dashboard
UNREGISTERED_DIMENSIONS = {
    "show_name": "customEvent:show_name",
    "audio_title": "customEvent:audio_title",
    "episode_name": "customEvent:episode_name",
}

# ─── Metrics ───
METRICS = {
    "eventCount": "Total Events",
    "totalUsers": "Distinct Users",
    "newUsers": "New Users",
    "activeUsers": "Active Users",
}

# ─── Brand Colors ───
COLORS = {
    "primary": "#6C3483",
    "secondary": "#2ECC71",
    "accent": "#E74C3C",
    "info": "#3498DB",
    "warning": "#F39C12",
    "dark": "#1A1A2E",
    "light": "#FAFAFA",
}

CHART_COLORS = [
    "#6C3483", "#2ECC71", "#E74C3C", "#3498DB", "#F39C12",
    "#1ABC9C", "#E67E22", "#9B59B6", "#2980B9", "#27AE60",
    "#D35400", "#8E44AD", "#16A085", "#C0392B", "#2C3E50",
]

# ─── Cache TTL (seconds) ───
DATA_CACHE_TTL = 3600       # 1 hour
FILTER_CACHE_TTL = 14400    # 4 hours
