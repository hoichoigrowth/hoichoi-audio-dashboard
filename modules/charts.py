"""
Plotly chart factory functions for the Hoichoi Audio Dashboard.
All charts use a consistent dark theme with brand colors.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from modules.constants import CHART_COLORS, COLORS


LAYOUT_DEFAULTS = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Calibri, sans-serif", color=COLORS["light"]),
    margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def daily_trend_chart(df: pd.DataFrame, metric: str = "eventCount") -> go.Figure:
    """Line chart: date vs selected metric."""
    metric_labels = {
        "eventCount": "Total Events",
        "totalUsers": "Distinct Users",
        "newUsers": "New Users",
        "activeUsers": "Active Users",
    }

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df[metric],
            mode="lines+markers",
            name=metric_labels.get(metric, metric),
            line=dict(color=COLORS["primary"], width=3),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(108, 52, 131, 0.15)",
        )
    )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=f"Daily {metric_labels.get(metric, metric)} Trend",
        xaxis_title="Date",
        yaxis_title=metric_labels.get(metric, metric),
        hovermode="x unified",
    )

    return fig


def metric_comparison_chart(df: pd.DataFrame) -> go.Figure:
    """Multi-line chart overlaying all metrics."""
    metrics = {
        "eventCount": ("Total Events", COLORS["primary"]),
        "totalUsers": ("Distinct Users", COLORS["info"]),
        "newUsers": ("New Users", COLORS["secondary"]),
        "activeUsers": ("Active Users", COLORS["warning"]),
    }

    fig = go.Figure()
    for metric, (label, color) in metrics.items():
        if metric in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["date"],
                    y=df[metric],
                    mode="lines+markers",
                    name=label,
                    line=dict(color=color, width=2),
                    marker=dict(size=4),
                )
            )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="All Metrics Comparison",
        xaxis_title="Date",
        yaxis_title="Count",
        hovermode="x unified",
    )

    return fig


def top_content_bar_chart(
    df: pd.DataFrame, metric: str = "eventCount", top_n: int = 15
) -> go.Figure:
    """Horizontal bar chart: content_title vs metric."""
    metric_labels = {
        "eventCount": "Total Events",
        "totalUsers": "Distinct Users",
        "newUsers": "New Users",
        "activeUsers": "Active Users",
    }

    plot_df = df.head(top_n).sort_values(metric, ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=plot_df[metric],
            y=plot_df["content_title"],
            orientation="h",
            marker=dict(
                color=plot_df[metric],
                colorscale=[[0, COLORS["info"]], [1, COLORS["primary"]]],
            ),
            text=plot_df[metric].apply(lambda x: f"{x:,}"),
            textposition="outside",
        )
    )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=f"Top {top_n} Content by {metric_labels.get(metric, metric)}",
        xaxis_title=metric_labels.get(metric, metric),
        yaxis_title="",
        height=max(400, top_n * 35),
    )

    return fig


def country_bar_chart(
    df: pd.DataFrame, metric: str = "eventCount", top_n: int = 15
) -> go.Figure:
    """Horizontal bar chart: country vs metric."""
    metric_labels = {
        "eventCount": "Total Events",
        "totalUsers": "Distinct Users",
        "newUsers": "New Users",
        "activeUsers": "Active Users",
    }

    plot_df = df.head(top_n).sort_values(metric, ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=plot_df[metric],
            y=plot_df["country"],
            orientation="h",
            marker=dict(
                color=plot_df[metric],
                colorscale=[[0, COLORS["secondary"]], [1, COLORS["accent"]]],
            ),
            text=plot_df[metric].apply(lambda x: f"{x:,}"),
            textposition="outside",
        )
    )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=f"Top Countries by {metric_labels.get(metric, metric)}",
        xaxis_title=metric_labels.get(metric, metric),
        yaxis_title="",
        height=max(300, top_n * 35),
    )

    return fig


def country_choropleth(df: pd.DataFrame, metric: str = "eventCount") -> go.Figure:
    """World choropleth map colored by metric."""
    metric_labels = {
        "eventCount": "Total Events",
        "totalUsers": "Distinct Users",
        "newUsers": "New Users",
        "activeUsers": "Active Users",
    }

    fig = px.choropleth(
        df,
        locations="country",
        locationmode="country names",
        color=metric,
        hover_name="country",
        color_continuous_scale=["#1A1A2E", COLORS["primary"], COLORS["accent"]],
        title=f"Geography: {metric_labels.get(metric, metric)}",
    )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="rgba(255,255,255,0.2)",
            bgcolor="rgba(0,0,0,0)",
            landcolor="rgba(30,30,50,0.8)",
            showocean=True,
            oceancolor="rgba(14,17,23,1)",
        ),
        height=450,
    )

    return fig


def content_trend_chart(
    df: pd.DataFrame, titles: list[str], metric: str = "eventCount"
) -> go.Figure:
    """Multi-line chart showing trends for selected content titles."""
    fig = go.Figure()

    for i, title in enumerate(titles):
        title_df = df[df["content_title"] == title].sort_values("date")
        if not title_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=title_df["date"],
                    y=title_df[metric],
                    mode="lines+markers",
                    name=title[:30] + ("..." if len(title) > 30 else ""),
                    line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=2),
                    marker=dict(size=4),
                )
            )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Content Trend Comparison",
        xaxis_title="Date",
        yaxis_title="Events",
        hovermode="x unified",
        height=400,
    )

    return fig


def donut_chart(df: pd.DataFrame, label_col: str, value_col: str, title: str) -> go.Figure:
    """Donut/pie chart for share visualization."""
    fig = go.Figure(
        data=[
            go.Pie(
                labels=df[label_col],
                values=df[value_col],
                hole=0.5,
                marker=dict(colors=CHART_COLORS[: len(df)]),
                textinfo="label+percent",
                textposition="outside",
            )
        ]
    )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=title,
        showlegend=False,
        height=400,
    )

    return fig
