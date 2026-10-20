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
_SINGLE_SERIES = {"light": "#2f6fe4", "dark": "#3987e5"}
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
        font=dict(family="Inter, system-ui, sans-serif"),
    )
    fig.update_xaxes(gridcolor=_GRID[mode], zeroline=False, tickfont=dict(color=_TEXT_MUTED[mode]))
    fig.update_yaxes(showgrid=False, tickfont=dict(color=_TEXT_MUTED[mode]))
    return fig


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    red, green, blue = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def demand_bar_chart(
    table: pd.DataFrame,
    categories: tuple[str, ...],
    n_posts: int,
    group_by_category: bool = True,
    mode: str = "light",
) -> go.Figure:
    """Horizontal stacked bars: in how many job posts each skill is requested.

    The solid part counts the posts that REQUIRE the skill, the hatched part
    the posts where it is only nice to have. One pair of traces per category
    gives a legend that doubles as a category filter (click to hide).
    """
    colors = category_colors(categories, mode)

    if group_by_category:
        rank = {category: i for i, category in enumerate(categories)}
        ordered = table.assign(_rank=table["category"].map(rank)).sort_values(
            ["_rank", "demand", "posts_count", "skill"], ascending=[True, False, False, True]
        )
    else:
        ordered = table
    # Plotly draws the first y category at the bottom: reverse to read top-down.
    y_order = list(ordered["skill"])[::-1]

    hovertemplate = (
        "<b>%{y}</b><br>%{customdata[0]}<br>"
        f"Required in %{{customdata[1]}} of {n_posts} posts<br>"
        "Nice to have in %{customdata[2]}<br>"
        "In your CV: %{customdata[3]}<extra></extra>"
    )
    fig = go.Figure()
    for category in categories:
        rows = ordered[ordered["category"] == category]
        if rows.empty:
            continue
        customdata = list(
            zip(
                rows["category"],
                rows["required_count"],
                rows["nice_count"],
                rows["in_cv"].map({True: "Yes", False: "No"}),
            )
        )
        color = colors[category]
        fig.add_trace(
            go.Bar(
                name=category, legendgroup=category, orientation="h",
                x=rows["required_count"], y=rows["skill"],
                marker=dict(color=color),
                customdata=customdata, hovertemplate=hovertemplate,
            )
        )
        fig.add_trace(
            go.Bar(
                name=f"{category} (nice to have)", legendgroup=category, showlegend=False,
                orientation="h", x=rows["nice_count"], y=rows["skill"],
                marker=dict(
                    color=_hex_to_rgba(color, 0.25),
                    line=dict(color=color, width=1),
                    pattern=dict(shape="/", fgcolor=color, size=6, solidity=0.3),
                ),
                customdata=customdata, hovertemplate=hovertemplate,
            )
        )

    # Total at the end of each bar, as plain text (not in the series colour).
    fig.add_trace(
        go.Scatter(
            # Small offset so the number does not touch the end of the bar.
            x=ordered["posts_count"] + 0.015 * max(1, ordered["posts_count"].max()),
            y=ordered["skill"], mode="text",
            text=ordered["posts_count"], textposition="middle right",
            textfont=dict(color=_TEXT_MUTED[mode]), showlegend=False, hoverinfo="skip",
            cliponaxis=False,
        )
    )
    # Legend key for the hatched part.
    if (ordered["nice_count"] > 0).any():
        fig.add_trace(
            go.Bar(
                name="Hatched = nice to have", orientation="h", x=[None], y=[None],
                marker=dict(
                    color="rgba(128,128,128,0.2)", line=dict(color="#888", width=1),
                    pattern=dict(shape="/", fgcolor="#888", size=6, solidity=0.3),
                ),
                hoverinfo="skip",
            )
        )

    fig.update_yaxes(categoryorder="array", categoryarray=y_order)
    fig.update_xaxes(title_text="Number of job posts", dtick=1 if n_posts <= 10 else None)
    fig.update_layout(
        barmode="stack",
        barcornerradius=4,
        legend=dict(orientation="h", yref="container", yanchor="top", y=1.0, xanchor="left", x=0, title_text=""),
    )
    height = max(260, 26 * len(ordered) + 120)
    # Room above the plot for the legend, which can wrap onto two rows.
    return _base_layout(fig, mode, height).update_layout(margin=dict(t=64))


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


def coverage_donut(score: float, mode: str = "light") -> go.Figure:
    """A ring showing the weighted coverage, with the percentage in the middle."""
    track = "#e6edfb" if mode == "light" else "#28456b"
    fig = go.Figure(
        go.Pie(
            values=[score, max(0.0, 100 - score)],
            hole=0.74,
            sort=False,
            direction="clockwise",
            marker=dict(colors=[_SINGLE_SERIES[mode], track], line=dict(width=0)),
            textinfo="none",
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(text=f"<b>{score:.0f}%</b>", x=0.5, y=0.55, showarrow=False,
                 font=dict(size=34, color=_SINGLE_SERIES[mode])),
            dict(text="weighted coverage", x=0.5, y=0.36, showarrow=False,
                 font=dict(size=12, color=_TEXT_MUTED[mode])),
        ],
    )
    return fig
