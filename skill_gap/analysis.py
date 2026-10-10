"""Turn extracted skills into the numbers shown in the app.

Everything is built on one pandas DataFrame, the "skill table", with one row
per skill requested in at least one job post:

    skill | category | posts_count | posts_share | in_cv

All other results (coverage score, study priorities, category breakdown) are
simple aggregations of that table, which keeps the logic easy to test and to
explain.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd

from skill_gap.skills_dictionary import SkillDictionary

SKILL_TABLE_COLUMNS = ["skill", "category", "posts_count", "posts_share", "in_cv"]


def build_skill_table(
    posts_skills: list[set[str]],
    cv_skills: set[str],
    dictionary: SkillDictionary,
) -> pd.DataFrame:
    """Count in how many posts each skill appears and flag the ones in the CV.

    Args:
        posts_skills: one set of skill names per job post.
        cv_skills: skill names found in the CV.
        dictionary: used to look up each skill's category.

    Returns:
        A DataFrame sorted by demand (most requested first, then by name so
        that ties are always shown in the same order).
    """
    n_posts = len(posts_skills)
    # Each set holds a skill at most once, so this counts posts, not mentions.
    counts = Counter(skill for skills in posts_skills for skill in skills)

    rows = [
        {
            "skill": skill,
            "category": dictionary.category_of(skill),
            "posts_count": count,
            "posts_share": count / n_posts,
            "in_cv": skill in cv_skills,
        }
        for skill, count in counts.items()
    ]
    table = pd.DataFrame(rows, columns=SKILL_TABLE_COLUMNS)
    if table.empty:
        return table
    return table.sort_values(
        ["posts_count", "skill"], ascending=[False, True], ignore_index=True
    )


def coverage_score(table: pd.DataFrame) -> float | None:
    """Percentage (0-100) of the requested skills covered by the CV, weighted.

    Each skill weighs as much as the number of posts that ask for it:

        coverage = sum(posts_count of skills in CV) / sum(posts_count of all skills)

    Example: SQL in 4 posts (in CV) and Tableau in 1 post (missing) gives
    4 / (4 + 1) = 80%, while an unweighted count would say 50%.

    Returns None when no skill was found in the job posts (nothing to cover).
    """
    if table.empty:
        return None
    total = table["posts_count"].sum()
    covered = table.loc[table["in_cv"], "posts_count"].sum()
    return float(100 * covered / total)


def study_priorities(table: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """The `n` most requested skills that are missing from the CV."""
    missing = table[~table["in_cv"]]
    # The table is already sorted by demand, so the first rows are the top ones.
    return missing.head(n).reset_index(drop=True)


def category_breakdown(table: pd.DataFrame, dictionary: SkillDictionary) -> pd.DataFrame:
    """Requested / covered skills and weighted coverage for each category.

    Categories follow the order declared in the dictionary; categories with no
    requested skill are left out.
    """
    columns = ["category", "requested", "covered", "coverage_pct"]
    if table.empty:
        return pd.DataFrame(columns=columns)

    weighted_covered = table["posts_count"].where(table["in_cv"], 0)
    grouped = (
        table.assign(weighted_covered=weighted_covered)
        .groupby("category")
        .agg(
            requested=("skill", "count"),
            covered=("in_cv", "sum"),
            weight_total=("posts_count", "sum"),
            weight_covered=("weighted_covered", "sum"),
        )
    )
    grouped["coverage_pct"] = 100 * grouped["weight_covered"] / grouped["weight_total"]

    order = [c for c in dictionary.categories if c in grouped.index]
    return grouped.loc[order].reset_index()[columns]


def extra_cv_skills(table: pd.DataFrame, cv_skills: set[str]) -> list[str]:
    """Skills in the CV that none of the job posts asked for (sorted A-Z)."""
    requested = set(table["skill"]) if not table.empty else set()
    return sorted(cv_skills - requested, key=str.lower)
