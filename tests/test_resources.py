from skill_gap.resources import load_resources, resources_for
from skill_gap.skills_dictionary import list_dictionaries, load_dictionary


def test_resources_use_known_skill_names():
    names = {s.name for p in list_dictionaries().values() for s in load_dictionary(p).skills}
    resources = load_resources()
    assert set(resources) <= names, set(resources) - names
    for items in resources.values():
        assert items and all(url.startswith("https://") for _, url in items)


def test_fallback_is_a_search_link():
    [(title, url)] = resources_for("Microsoft Office", {})
    assert "Microsoft Office" in title and url.startswith("https://www.google.com/search?q=")
