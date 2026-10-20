"""Skills for a role without a dictionary are detected in the job posts."""

from skill_gap.analysis import build_skill_table
from skill_gap.extractor import find_skills, find_skills_in_posts
from skill_gap.keywords import CUSTOM_CATEGORY, add_custom_skills, merge_dictionaries, suggest_terms
from skill_gap.skills_dictionary import list_dictionaries, load_dictionary

# Fictional posts for a role with no ready-made list.
NURSE_POSTS = [
    "Infermiere per terapia intensiva. Requisiti: iscrizione OPI, BLSD, cartella clinica elettronica, Excel.",
    "Cerchiamo infermiere con BLSD e ACLS. Esperienza in terapia intensiva. Iscrizione all'albo OPI.",
    "Registered Nurse, ICU. BLS and ACLS certification required. Good communication skills.",
]


def all_skills():
    return merge_dictionaries([load_dictionary(p) for p in list_dictionaries().values()], "Nurse")


def test_merge_keeps_one_skill_per_name():
    merged = all_skills()
    names = [s.name for s in merged.skills]
    assert len(names) == len(set(names))
    assert {"Excel", "SQL", "SEO", "Payroll", "Recruiting", "Communication"} <= set(names)


def test_suggests_recurring_terms_not_in_the_dictionaries():
    terms = suggest_terms(NURSE_POSTS, all_skills(), role="Infermiere")
    assert {"Terapia intensiva", "BLSD", "ACLS", "OPI"} <= set(terms)
    # Known skills, common words and the role itself are not suggested.
    lowered = {t.lower() for t in terms}
    assert not lowered & {"excel", "communication", "esperienza", "requisiti", "infermiere"}


def test_custom_skills_are_matched_and_counted():
    dictionary = add_custom_skills(all_skills(), ["BLSD", "ACLS", "Terapia intensiva", "Excel"])
    assert CUSTOM_CATEGORY in dictionary.categories
    assert sum(s.name == "Excel" for s in dictionary.skills) == 1  # not added twice
    cv_skills = find_skills("Infermiera con certificazione BLSD ed esperienza in terapia intensiva.", dictionary)
    table = build_skill_table(find_skills_in_posts(NURSE_POSTS, dictionary), cv_skills, dictionary)
    rows = table.set_index("skill")
    assert rows.loc["BLSD", "in_cv"] and rows.loc["Terapia intensiva", "in_cv"]
    assert not rows.loc["ACLS", "in_cv"]
    assert rows.loc["ACLS", "category"] == CUSTOM_CATEGORY
