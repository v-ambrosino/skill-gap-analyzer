"""Build a self-contained HTML report of the results, to download.

The report is a single HTML file with inline CSS: it opens in any browser
and prints cleanly to PDF ("Print > Save as PDF"), with no extra dependency.

Privacy: the report lists skill names, counts and scores only. It never
contains the text of the CV or of the job posts.
"""

from __future__ import annotations

from datetime import date
from html import escape

import pandas as pd

_STYLE = """
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       color: #1f1f1e; background: #ffffff; max-width: 820px; margin: 32px auto; padding: 0 16px;
       line-height: 1.45; }
h1 { font-size: 26px; margin-bottom: 4px; }
h2 { font-size: 18px; margin-top: 32px; border-bottom: 1px solid #e3e2de; padding-bottom: 4px; }
.meta { color: #52514e; font-size: 13px; }
.kpis { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 20px; }
.kpi { border: 1px solid #e3e2de; border-radius: 8px; padding: 12px 16px; min-width: 150px; }
.kpi .value { font-size: 26px; font-weight: 600; }
.kpi .label { color: #52514e; font-size: 13px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #ecebe8; }
th { color: #52514e; font-weight: 600; }
td.num, th.num { text-align: right; }
.badge { display: inline-block; border-radius: 6px; padding: 2px 8px; margin: 2px; font-size: 13px; }
.present { background: #e6f4e6; color: #006300; }
.missing { background: #fbe9e9; color: #a32121; }
.note { color: #52514e; font-size: 12.5px; margin-top: 32px; }
@media print { body { margin: 0 auto; } h2 { break-after: avoid; } table { break-inside: auto; } }
"""


def _badges(table: pd.DataFrame, css_class: str, mark: str) -> str:
    if table.empty:
        return "<p><em>None.</em></p>"
    return "<p>" + "".join(
        f'<span class="badge {css_class}">{mark} {escape(row.skill)} &middot; {row.posts_count}</span>'
        for row in table.itertuples()
    ) + "</p>"


def build_html_report(
    table: pd.DataFrame,
    breakdown: pd.DataFrame,
    priorities: pd.DataFrame,
    extras: list[str],
    *,
    role: str,
    n_posts: int,
    coverage: float,
    nice_weight: float,
    version: str,
    generated_on: date | None = None,
) -> str:
    """Return the full HTML document as a string.

    Args:
        table: the skill table from `analysis.build_skill_table`.
        breakdown: the output of `analysis.category_breakdown`.
        priorities: the output of `analysis.study_priorities`.
        extras: skills in the CV that no post asked for.
        role: the target role (dictionary name) shown in the header.
        n_posts: number of job posts analysed.
        coverage: weighted coverage score, 0-100.
        nice_weight: weight used for nice-to-have skills.
        version: app version, printed in the footer.
        generated_on: report date (defaults to today).
    """
    generated_on = generated_on or date.today()
    present = table[table["in_cv"]]
    missing = table[~table["in_cv"]]

    priority_rows = "".join(
        f"<tr><td class='num'>{i}</td><td>{escape(row.skill)}</td><td>{escape(row.category)}</td>"
        f"<td class='num'>{row.required_count}</td><td class='num'>{row.nice_count}</td>"
        f"<td class='num'>{row.posts_share * 100:.0f}%</td></tr>"
        for i, row in enumerate(priorities.itertuples(), start=1)
    )
    category_rows = "".join(
        f"<tr><td>{escape(row.category)}</td><td class='num'>{row.covered} of {row.requested}</td>"
        f"<td class='num'>{row.coverage_pct:.0f}%</td></tr>"
        for row in breakdown.itertuples()
    )
    skill_rows = "".join(
        f"<tr><td>{escape(row.skill)}</td><td>{escape(row.category)}</td>"
        f"<td class='num'>{row.required_count}</td><td class='num'>{row.nice_count}</td>"
        f"<td class='num'>{row.demand:g}</td><td>{'Yes' if row.in_cv else 'No'}</td></tr>"
        for row in table.itertuples()
    )
    extras_html = (
        f"<p>Also in your CV but not requested by these posts: {escape(', '.join(extras))}.</p>"
        if extras else ""
    )
    priorities_html = (
        "<table><tr><th class='num'>#</th><th>Skill</th><th>Category</th><th class='num'>Required</th>"
        f"<th class='num'>Nice</th><th class='num'>Share of posts</th></tr>{priority_rows}</table>"
        if not priorities.empty else "<p>Your CV covers every requested skill.</p>"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skill Gap Report</title>
<style>{_STYLE}</style>
</head>
<body>
<h1>Skill Gap Report</h1>
<div class="meta">Target role: <strong>{escape(role)}</strong> &middot; {n_posts} job posts analysed &middot;
generated on {generated_on.isoformat()}</div>

<div class="kpis">
  <div class="kpi"><div class="value">{coverage:.0f}%</div><div class="label">Weighted coverage</div></div>
  <div class="kpi"><div class="value">{len(present)} of {len(table)}</div><div class="label">Requested skills in your CV</div></div>
  <div class="kpi"><div class="value">{len(missing)}</div><div class="label">Missing skills</div></div>
</div>

<h2>Top {len(priorities)} study priorities</h2>
{priorities_html}

<h2>Coverage by category</h2>
<table><tr><th>Category</th><th class="num">Skills in CV</th><th class="num">Weighted coverage</th></tr>{category_rows}</table>

<h2>Your CV vs the market</h2>
<p>The number next to each skill is how many job posts ask for it.</p>
<h3>In your CV ({len(present)})</h3>
{_badges(present, "present", "&#10003;")}
<h3>Missing from your CV ({len(missing)})</h3>
{_badges(missing, "missing", "&#10007;")}
{extras_html}

<h2>All requested skills</h2>
<table><tr><th>Skill</th><th>Category</th><th class="num">Required in</th><th class="num">Nice to have in</th>
<th class="num">Demand</th><th>In CV</th></tr>{skill_rows}</table>

<p class="note">How to read it: demand = posts that require the skill + {nice_weight:g} &times; posts where it
is only nice to have. Weighted coverage = demand of the skills in your CV / total demand. Skills are
recognised with a dictionary (no AI), so wording outside the dictionary can be missed.
This report contains skill names and scores only, never the text of your CV or of the job posts.
Generated by Skill Gap Analyzer v{escape(version)}.</p>
</body>
</html>
"""
