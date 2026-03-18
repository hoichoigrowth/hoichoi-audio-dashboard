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


def dual_axis_users_chart(df: pd.DataFrame) -> go.Figure:
    """Dual Y-axis chart: Distinct Users (left axis) + New Users (right axis)."""
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Left axis — Distinct Users (bar)
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df["totalUsers"],
            name="Distinct Users",
            marker=dict(color=COLORS["info"], opacity=0.7),
        ),
        secondary_y=False,
    )

    # Right axis — New Users (line)
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["newUsers"],
            mode="lines+markers",
            name="New Users",
            line=dict(color=COLORS["secondary"], width=3),
            marker=dict(size=6),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Distinct Users & New Users (Daily)",
        hovermode="x unified",
        barmode="overlay",
    )
    fig.update_yaxes(title_text="Distinct Users", secondary_y=False)
    fig.update_yaxes(title_text="New Users", secondary_y=True)

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


def top_content_bar_chart_generic(
    df: pd.DataFrame, label_col: str, metric: str, title: str, top_n: int = 15
) -> go.Figure:
    """Horizontal bar chart: any label column vs any metric column."""
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
            y=plot_df[label_col],
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
        title=title,
        xaxis_title=metric_labels.get(metric, metric),
        yaxis_title="",
        height=max(300, min(top_n, len(plot_df)) * 35),
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


def _grouped_stacked_bar(
    labels: pd.Series,
    event_counts: pd.Series,
    active_users: pd.Series,
    new_users: pd.Series,
    title: str,
    label_col_name: str = "show_name",
    height: int = 500,
    metric_mode: str = "both",
) -> go.Figure:
    """
    Horizontal bar chart with configurable metric display.
    metric_mode:
      "both"        — Events bar + Distinct Users bar (Active + New stacked)
      "event_count"  — Events bar only
      "unique_users" — Distinct Users bar only (Active + New stacked)
    """
    fig = go.Figure()

    if metric_mode in ("both", "event_count"):
        fig.add_trace(
            go.Bar(
                y=labels,
                x=event_counts,
                name="Events",
                orientation="h",
                marker=dict(color=COLORS["accent"]),
                text=event_counts.apply(lambda x: f"{x:,}"),
                textposition="outside",
                offsetgroup="events",
            )
        )

    if metric_mode in ("both", "unique_users"):
        total_users = active_users + new_users
        fig.add_trace(
            go.Bar(
                y=labels,
                x=active_users,
                name="Active Users",
                orientation="h",
                marker=dict(color=COLORS["info"]),
                text=total_users.apply(lambda x: f"{x:,}"),
                textposition="outside",
                offsetgroup="users",
            )
        )
        fig.add_trace(
            go.Bar(
                y=labels,
                x=new_users,
                name="New Users",
                orientation="h",
                marker=dict(color=COLORS["secondary"]),
                offsetgroup="users",
                base=active_users.values,
            )
        )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title=title,
        xaxis_title="Count",
        yaxis_title="",
        barmode="group",
        height=height,
        bargroupgap=0.15,
    )

    return fig


def show_grouped_bar_chart(df: pd.DataFrame, top_n: int = 20, metric_mode: str = "both") -> go.Figure:
    """
    Horizontal grouped bar chart at show level.
    metric_mode controls which bars are displayed.
    """
    plot_df = df.head(top_n).sort_values("eventCount", ascending=True)
    return _grouped_stacked_bar(
        labels=plot_df["show_name"],
        event_counts=plot_df["eventCount"],
        active_users=plot_df["activeUsers"],
        new_users=plot_df["newUsers"],
        title=f"Top {top_n} Shows: Events vs Distinct Users",
        height=max(500, top_n * 50),
        metric_mode=metric_mode,
    )


def episode_drilldown_chart(df: pd.DataFrame, show_name: str, metric_mode: str = "both") -> go.Figure:
    """
    Horizontal grouped bar for episodes within a show.
    Episodes sorted ascending by ep number (Ep 1 at top). metric_mode controls bars displayed.
    """
    show_df = df[df["show_name"] == show_name].copy()

    if "ep_no" in show_df.columns:
        show_df["ep_no_num"] = pd.to_numeric(show_df["ep_no"], errors="coerce").fillna(0)
        # Sort descending so Plotly renders Ep 1 at the TOP of the horizontal bar chart
        show_df = show_df.sort_values("ep_no_num", ascending=False)
    else:
        show_df = show_df.sort_values("eventCount", ascending=True)

    return _grouped_stacked_bar(
        labels=show_df["content_title"],
        event_counts=show_df["eventCount"],
        active_users=show_df["activeUsers"],
        new_users=show_df["newUsers"],
        title=f"📺 {show_name} — Episodes",
        height=max(400, len(show_df) * 50),
        metric_mode=metric_mode,
    )


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
