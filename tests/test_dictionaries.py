"""Tests for the role dictionaries: listing, includes and the Data Engineer file."""

import pytest

from skill_gap.extractor import NICE_TO_HAVE, find_skill_mentions, find_skills
from skill_gap.skills_dictionary import (
    DictionaryError,
    list_dictionaries,
    load_dictionary,
)


@pytest.fixture(scope="module")
def data_engineering():
    return load_dictionary(list_dictionaries()["Data Engineer / Analytics Engineer"])


def test_every_dictionary_is_valid():
    dictionaries = list_dictionaries()
    # The default (Data Analyst) dictionary is listed first.
    assert list(dictionaries)[0] == "Data Analyst / BI / Business Analyst"
    for path in dictionaries.values():
        dictionary = load_dictionary(path)
        assert 40 <= len(dictionary.skills) <= 120, path.name
        assert dictionary.description


def test_shared_soft_skills_are_included(data_engineering):
    soft_skills = {s.name for s in data_engineering.skills if s.category == "Soft Skills"}
    assert {"Communication", "Teamwork", "Problem Solving", "English"} <= soft_skills


def test_include_needs_the_category(tmp_path):
    (tmp_path / "shared.yaml").write_text(
        "skills:\n  - {name: Teamwork, category: Soft Skills, synonyms: [teamwork]}\n"
    )
    (tmp_path / "role.yaml").write_text(
        "domain: Test\ncategories: [Tools]\ninclude: [shared.yaml]\n"
        "skills:\n  - {name: Excel, category: Tools, synonyms: [excel]}\n"
    )
    with pytest.raises(DictionaryError, match="unknown category"):
        load_dictionary(tmp_path / "role.yaml")


DATA_ENGINEER_POST = """
Data Engineer (fictional)
Requirements:
- Batch and streaming pipelines with Spark and Kafka
- Strong Python and SQL; Scala is a plus
- Airflow, dbt and Snowflake on AWS (S3, Glue, Lambda)
- Terraform, CI/CD with GitHub Actions, Docker
Nice to have: Kubernetes, Delta Lake, Go.
Lavoriamo su larga scala; JavaScript nel frontend. Ottime capacità di comunicazione.
"""


def test_data_engineer_post(data_engineering):
    mentions = find_skill_mentions(DATA_ENGINEER_POST, data_engineering)
    assert {
        "Batch Processing", "Apache Spark", "Apache Kafka", "Python", "SQL", "Scala",
        "Apache Airflow", "dbt", "Snowflake", "AWS", "Amazon S3", "AWS Glue",
        "AWS Lambda", "Infrastructure as Code", "CI/CD", "Docker", "Kubernetes",
        "Delta Lake / Iceberg", "Go", "Communication",
    } <= set(mentions)
    for skill in ["Scala", "Kubernetes", "Delta Lake / Iceberg", "Go"]:
        assert mentions[skill].priority == NICE_TO_HAVE, skill


@pytest.mark.parametrize(
    "text, skill",
    [
        ("Progetti su larga scala", "Scala"),     # Italian word, not the language
        ("Frontend in JavaScript", "Java"),       # different language
        ("Let's go live next month", "Go"),       # plain English verb
        ("Go to market in Q3", "Go"),             # sentence start, not in a list
    ],
)
def test_data_engineer_false_positives(data_engineering, text, skill):
    assert skill not in find_skills(text, data_engineering)


def test_go_after_a_preposition(data_engineering):
    assert "Go" in find_skills("Gradita la conoscenza di Go.", data_engineering)
    assert "Go" in find_skills("Experience with Go is a plus", data_engineering)


def test_sample_data_matches_its_role():
    from skill_gap.extractor import find_skills_in_posts, split_job_posts
    from skill_gap.skills_dictionary import DICTIONARIES_DIR

    samples = DICTIONARIES_DIR.parent / "samples"
    # The default role must have samples: the app falls back to them for the other roles.
    assert (samples / "data_analytics").is_dir()
    for path in list_dictionaries().values():
        folder = samples / path.stem
        if not folder.is_dir():
            continue
        posts = split_job_posts((folder / "job_posts.txt").read_text(encoding="utf-8"))
        cv = (folder / "cv.txt").read_text(encoding="utf-8")
        dictionary = load_dictionary(path)
        assert len(posts) >= 3, path.stem
        assert all(find_skills_in_posts(posts, dictionary)), path.stem
        assert find_skills(cv, dictionary), path.stem


def test_ways_of_working_are_soft_skills_everywhere():
    """They are shown with examples in the CV, so they must never become study priorities."""
    from skill_gap.resources import load_cv_phrases

    soft = {
        "Agile", "Scrum", "Kanban", "Waterfall", "Documentation", "Business Acumen", "Requirements Gathering",
        "Data Storytelling", "Negotiation", "Customer Service", "Closing", "Cold Calling", "Sales Presentations",
        "Employee Relations", "Diversity & Inclusion", "Driving Licence",
    }
    phrases = load_cv_phrases()
    for path in list_dictionaries().values():
        for skill in load_dictionary(path).skills:
            if skill.name in soft:
                assert skill.category == "Soft Skills", (path.name, skill.name)
            if skill.category == "Soft Skills":
                assert phrases.get(skill.name), (path.name, skill.name)
