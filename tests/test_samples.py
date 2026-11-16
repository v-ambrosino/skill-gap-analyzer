"""Every role has fictional sample data that gives a meaningful demo."""

from pathlib import Path

import pytest

from skill_gap.analysis import (
    build_skill_table,
    coverage_score,
    post_matches,
    split_soft_skills,
    study_priorities,
)
from skill_gap.extractor import find_skill_mentions, find_skills_in_posts, split_job_posts
from skill_gap.skills_dictionary import list_dictionaries, load_dictionary

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


@pytest.mark.parametrize("path", list_dictionaries().values(), ids=lambda p: p.stem)
def test_sample_data_gives_a_meaningful_result(path):
    dictionary = load_dictionary(path)
    folder = SAMPLES / path.stem
    posts = split_job_posts((folder / "job_posts.txt").read_text(encoding="utf-8"))
    cv_skills = set(find_skill_mentions((folder / "cv.txt").read_text(encoding="utf-8"), dictionary))
    assert len(posts) >= 3

    mentions = find_skills_in_posts(posts, dictionary)
    technical, soft = split_soft_skills(build_skill_table(mentions, cv_skills, dictionary))
    # Neither a perfect CV nor an empty one: the demo must show both sides.
    assert 25 <= coverage_score(technical) <= 80
    assert len(study_priorities(technical)) == 5
    assert not soft.empty
    assert post_matches(mentions, cv_skills, dictionary)["coverage"].notna().all()
