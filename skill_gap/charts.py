"""Plotly charts for the app.

Kept separate from app.py so the UI file only deals with layout and state.
Colours are fixed per category (never per rank), so a category keeps its
colour when filters change the bars on screen.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

# Categorical palette in a fixed order, checked for colour-blind separation.
# Each mode has its own steps, tuned for a light or dark background.
_CATEGORY_PALETTE = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
}
_SINGLE_SERIES = {"light": "#2a78d6", "dark": "#3987e5"}
_TEXT_MUTED = {"light": "#52514e", "dark": "#c3c2b7"}
_GRID = {"light": "rgba(0,0,0,0.08)", "dark": "rgba(255,255,255,0.10)"}


def category_colors(categories: list[str] | tuple[str, ...], mode: str = "light") -> dict[str, str]:
    """Map each category (in dictionary order) to its fixed palette colour."""
    palette = _CATEGORY_PALETTE.get(mode, _CATEGORY_PALETTE["light"])
    return {category: palette[i % len(palette)] for i, category in enumerate(categories)}


def _base_layout(fig: go.Figure, mode: str, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=24, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        bargap=0.25,
        hoverlabel=dict(align="left"),
    )
    fig.update_xaxes(gridcolor=_GRID[mode], zeroline=False, tickfont=dict(color=_TEXT_MUTED[mode]))
    fig.update_yaxes(showgrid=False, tickfont=dict(color=_TEXT_MUTED[mode]))
    return fig


def demand_bar_chart(
    table: pd.DataFrame,
    categories: tuple[str, ...],
    n_posts: int,
    group_by_category: bool = True,
    mode: str = "light",
) -> go.Figure:
    """Horizontal bars: in how many job posts each skill is requested.

    One trace per category gives a legend that doubles as a category filter
    (click a legend entry to hide it).
    """
    colors = category_colors(categories, mode)

    if group_by_category:
        rank = {category: i for i, category in enumerate(categories)}
        ordered = table.assign(_rank=table["category"].map(rank)).sort_values(
            ["_rank", "posts_count", "skill"], ascending=[True, False, True]
        )
    else:
        ordered = table
    # Plotly draws the first y category at the bottom: reverse to read top-down.
    y_order = list(ordered["skill"])[::-1]

    fig = go.Figure()
    for category in categories:
        rows = ordered[ordered["category"] == category]
        if rows.empty:
            continue
        in_cv_label = rows["in_cv"].map({True: "Yes", False: "No"})
        fig.add_trace(
            go.Bar(
                name=category,
                orientation="h",
                x=rows["posts_count"],
                y=rows["skill"],
                marker=dict(color=colors[category], cornerradius=4),
                text=rows["posts_count"],
                textposition="outside",
                cliponaxis=False,
                customdata=list(zip(rows["category"], rows["posts_share"] * 100, in_cv_label)),
                hovertemplate=(
                    "<b>%{y}</b><br>%{customdata[0]}<br>"
                    f"Requested in %{{x}} of {n_posts} posts (%{{customdata[1]:.0f}}%)<br>"
                    "In your CV: %{customdata[2]}<extra></extra>"
                ),
            )
        )

    fig.update_yaxes(categoryorder="array", categoryarray=y_order)
    fig.update_xaxes(title_text="Number of job posts", dtick=1 if n_posts <= 10 else None)
    fig.update_layout(
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text=""),
    )
    height = max(260, 26 * len(ordered) + 80)
    return _base_layout(fig, mode, height)


def category_coverage_chart(breakdown: pd.DataFrame, mode: str = "light") -> go.Figure:
    """Horizontal bars: weighted CV coverage (%) for each category."""
    labels = [
        f"{pct:.0f}%  ({covered} of {requested})"
        for pct, covered, requested in zip(
            breakdown["coverage_pct"], breakdown["covered"], breakdown["requested"]
        )
    ]
    fig = go.Figure(
        go.Bar(
            orientation="h",
            x=breakdown["coverage_pct"],
            y=breakdown["category"],
            marker=dict(color=_SINGLE_SERIES[mode], cornerradius=4),
            text=labels,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Weighted coverage: %{x:.0f}%<extra></extra>",
        )
    )
    fig.update_xaxes(range=[0, 135], tickvals=[0, 25, 50, 75, 100], ticksuffix="%",
                     title_text="Weighted coverage")
    fig.update_yaxes(autorange="reversed")
    height = max(200, 44 * len(breakdown) + 70)
    return _base_layout(fig, mode, height)
