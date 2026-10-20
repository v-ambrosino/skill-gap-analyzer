"""Turn extracted skills into the numbers shown in the app.

Everything is built on one pandas DataFrame, the "skill table", with one row
per skill requested in at least one job post:

    skill | category | posts_count | required_count | nice_count | demand | posts_share | in_cv

`demand` is the weight used everywhere else: a post that REQUIRES a skill adds
1, a post where the skill is only NICE TO HAVE adds `nice_weight` (0.5 by
default). All other results (coverage score, study priorities, category
breakdown) are simple aggregations of that table, which keeps the logic easy
to test and to explain.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from skill_gap.extractor import NICE_TO_HAVE, REQUIRED, SkillMention
from skill_gap.skills_dictionary import SkillDictionary

DEFAULT_NICE_WEIGHT = 0.5

# Soft skills are reported on their own: they are shown in the CV through
# examples rather than studied, so they are kept out of the coverage score,
# the missing skills and the study priorities.
SOFT_SKILLS_CATEGORY = "Soft Skills"

SKILL_TABLE_COLUMNS = [
    "skill", "category", "posts_count", "required_count", "nice_count",
    "demand", "posts_share", "in_cv",
]

# What one job post contributes: its skills, either as a plain set (all
# required) or as a mapping skill -> SkillMention / priority string.
PostSkills = set[str] | Mapping[str, SkillMention | str]


def _priorities(post: PostSkills) -> dict[str, str]:
    """Normalise one post's skills to a {skill: priority} dict."""
    if isinstance(post, (set, frozenset)):
        return {skill: REQUIRED for skill in post}
    return {
        skill: value.priority if isinstance(value, SkillMention) else value
        for skill, value in post.items()
    }


def build_skill_table(
    posts_skills: list[PostSkills],
    cv_skills: set[str],
    dictionary: SkillDictionary,
    nice_weight: float = DEFAULT_NICE_WEIGHT,
) -> pd.DataFrame:
    """Count in how many posts each skill appears and flag the ones in the CV.

    Args:
        posts_skills: one entry per job post (see `PostSkills`).
        cv_skills: skill names found in the CV.
        dictionary: used to look up each skill's category.
        nice_weight: weight of a "nice to have" mention (0 = ignore them,
            1 = same as a requirement).

    Returns:
        A DataFrame sorted by demand (then by number of posts, then by name so
        that ties are always shown in the same order).
    """
    n_posts = len(posts_skills)
    required: dict[str, int] = {}
    nice: dict[str, int] = {}
    # Each post holds a skill at most once, so this counts posts, not mentions.
    for post in posts_skills:
        for skill, priority in _priorities(post).items():
            target = nice if priority == NICE_TO_HAVE else required
            target[skill] = target.get(skill, 0) + 1

    rows = []
    for skill in required.keys() | nice.keys():
        n_required, n_nice = required.get(skill, 0), nice.get(skill, 0)
        rows.append(
            {
                "skill": skill,
                "category": dictionary.category_of(skill),
                "posts_count": n_required + n_nice,
                "required_count": n_required,
                "nice_count": n_nice,
                "demand": n_required + nice_weight * n_nice,
                "posts_share": (n_required + n_nice) / n_posts,
                "in_cv": skill in cv_skills,
            }
        )
    table = pd.DataFrame(rows, columns=SKILL_TABLE_COLUMNS)
    if table.empty:
        return table
    return table.sort_values(
        ["demand", "posts_count", "skill"], ascending=[False, False, True], ignore_index=True
    )


def split_soft_skills(
    table: pd.DataFrame, category: str = SOFT_SKILLS_CATEGORY
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the skill table into (technical skills, soft skills), keeping the order."""
    is_soft = table["category"] == category
    return (
        table[~is_soft].reset_index(drop=True),
        table[is_soft].reset_index(drop=True),
    )


def coverage_score(table: pd.DataFrame) -> float | None:
    """Percentage (0-100) of the requested skills covered by the CV, weighted.

    Each skill weighs as much as its demand (posts that require it, plus half
    a point for each post where it is only nice to have):

        coverage = sum(demand of skills in CV) / sum(demand of all skills)

    Example: SQL required by 4 posts (in CV) and Tableau required by 1 post
    (missing) gives 4 / (4 + 1) = 80%, while an unweighted count would say 50%.

    Returns None when there is nothing to cover: no skill found in the posts,
    or only nice-to-have skills with a weight of 0.
    """
    if table.empty:
        return None
    total = table["demand"].sum()
    if total == 0:
        return None
    covered = table.loc[table["in_cv"], "demand"].sum()
    return float(100 * covered / total)


def study_priorities(table: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """The `n` missing skills with the highest demand."""
    missing = table[~table["in_cv"] & (table["demand"] > 0)]
    # The table is already sorted by demand, so the first rows are the top ones.
    return missing.head(n).reset_index(drop=True)


def category_breakdown(table: pd.DataFrame, dictionary: SkillDictionary) -> pd.DataFrame:
    """Requested / covered skills and weighted coverage for each category.

    Categories follow the order declared in the dictionary; categories with no
    requested skill (or zero total demand) are left out.
    """
    columns = ["category", "requested", "covered", "coverage_pct"]
    if table.empty:
        return pd.DataFrame(columns=columns)

    weighted_covered = table["demand"].where(table["in_cv"], 0)
    grouped = (
        table.assign(weighted_covered=weighted_covered)
        .groupby("category")
        .agg(
            requested=("skill", "count"),
            covered=("in_cv", "sum"),
            weight_total=("demand", "sum"),
            weight_covered=("weighted_covered", "sum"),
        )
    )
    grouped = grouped[grouped["weight_total"] > 0]
    grouped["coverage_pct"] = 100 * grouped["weight_covered"] / grouped["weight_total"]

    order = [c for c in dictionary.categories if c in grouped.index]
    return grouped.loc[order].reset_index()[columns]


def extra_cv_skills(table: pd.DataFrame, cv_skills: set[str]) -> list[str]:
    """Skills in the CV that none of the job posts asked for (sorted A-Z)."""
    requested = set(table["skill"]) if not table.empty else set()
    return sorted(cv_skills - requested, key=str.lower)
