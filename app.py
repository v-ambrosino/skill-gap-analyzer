"""Skill Gap Analyzer: Streamlit user interface.

Run locally with:  streamlit run app.py

This file only handles layout, user input and session state. All the logic
lives in the `skill_gap` package:
    pdf_reader -> extractor -> analysis -> charts
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from skill_gap import __version__
from skill_gap.analysis import (
    build_skill_table,
    category_breakdown,
    coverage_score,
    extra_cv_skills,
    study_priorities,
)
from skill_gap.charts import category_coverage_chart, demand_bar_chart
from skill_gap.extractor import find_skills, find_skills_in_posts, split_job_posts
from skill_gap.pdf_reader import PdfReadError, extract_text_from_pdf
from skill_gap.skills_dictionary import DictionaryError, SkillDictionary, load_dictionary

SAMPLES_DIR = Path(__file__).resolve().parent / "data" / "samples"
MODE_SINGLE_BOX = "One text box (separate posts with ---)"
MODE_FIELDS = "One field per job post"
TOP_PRIORITIES = 5
ISSUES_URL = "https://github.com/v-ambrosino/skill-gap-analyzer/issues"

st.set_page_config(page_title="Skill Gap Analyzer", page_icon=":material/insights:", layout="wide")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_resource
def get_dictionary() -> SkillDictionary:
    """Load the skill dictionary once per server process.

    Only the dictionary is cached. The CV and the job posts are NEVER cached,
    so they cannot leak between users or outlive the session.
    """
    return load_dictionary()


def read_sample(name: str) -> str:
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Session state and button callbacks
# ---------------------------------------------------------------------------
# Session state lives in the server's memory for this browser tab only.
# It disappears when the tab is closed or the session times out.
def init_state() -> None:
    st.session_state.setdefault("post_ids", [0])  # ids of the dynamic fields
    st.session_state.setdefault("next_post_id", 1)
    st.session_state.setdefault("posts_text", "")
    st.session_state.setdefault("cv_text_manual", "")


def add_post_field() -> None:
    st.session_state.post_ids.append(st.session_state.next_post_id)
    st.session_state.next_post_id += 1


def remove_post_field(post_id: int) -> None:
    st.session_state.post_ids.remove(post_id)
    st.session_state.pop(f"post_{post_id}", None)
    if not st.session_state.post_ids:  # always keep at least one field
        add_post_field()


def load_sample_data() -> None:
    """Fill both input modes and the CV text box with the fictional samples."""
    clear_all()
    sample_posts = read_sample("job_posts.txt")
    st.session_state.posts_text = sample_posts
    posts = split_job_posts(sample_posts)
    st.session_state.post_ids = list(range(len(posts)))
    st.session_state.next_post_id = len(posts)
    for post_id, post in enumerate(posts):
        st.session_state[f"post_{post_id}"] = post
    st.session_state.cv_text_manual = read_sample("cv.txt")


def clear_all() -> None:
    for post_id in st.session_state.post_ids:
        st.session_state.pop(f"post_{post_id}", None)
    st.session_state.post_ids = [0]
    st.session_state.next_post_id = 1
    st.session_state.posts_text = ""
    st.session_state.cv_text_manual = ""
    # Changing the uploader key is the way to reset a st.file_uploader.
    st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1


# ---------------------------------------------------------------------------
# UI building blocks
# ---------------------------------------------------------------------------
def render_sidebar(dictionary: SkillDictionary) -> None:
    with st.sidebar:
        st.header(":material/lock: Privacy")
        st.markdown(
            "**No data is stored.** Your CV and the job posts are processed "
            "**in memory only** for this session: nothing is saved to disk, "
            "logged, cached or sent to external services or AI. Close the tab "
            "and everything is gone."
        )
        st.divider()
        st.header(":material/help: How it works")
        st.markdown(
            "1. Skills are recognised with an editable **dictionary** "
            f"of **{len(dictionary.skills)} skills** (English and Italian synonyms).\n"
            "2. Each skill counts **once per job post**.\n"
            "3. **Coverage** = share of the requested skills found in your CV, "
            "weighted by how many posts ask for each skill."
        )
        st.caption("Categories: " + ", ".join(dictionary.categories))


def render_cv_input() -> str:
    """Return the CV text, from the uploaded PDF or from the text box."""
    st.subheader("1. Your CV")
    uploaded = st.file_uploader(
        "Upload your CV (PDF)",
        type=["pdf"],
        key=f"cv_upload_{st.session_state.get('uploader_key', 0)}",
        help="Text-based PDFs only: scanned images cannot be read.",
    )
    with st.expander("No PDF at hand? Paste your CV text instead", expanded=False):
        st.text_area("CV text", key="cv_text_manual", height=200, label_visibility="collapsed")

    if uploaded is not None:
        try:
            text = extract_text_from_pdf(uploaded.getvalue())
        except PdfReadError as exc:
            st.error(f":material/error: {exc}")
            return ""
        if not text:
            st.warning(
                ":material/warning: No text found in this PDF. It is probably a scanned "
                "image: export your CV as a text PDF, or paste its text above."
            )
        else:
            st.caption(f":material/check_circle: Read {len(text.split()):,} words from **{uploaded.name}**.")
        return text
    return st.session_state.cv_text_manual


def render_posts_input() -> list[str]:
    """Return the list of job posts, from either input mode."""
    st.subheader("2. Job posts")
    mode = st.radio("Input mode", [MODE_SINGLE_BOX, MODE_FIELDS], horizontal=True, key="input_mode")

    if mode == MODE_SINGLE_BOX:
        st.text_area(
            "Paste one or more job posts (English or Italian)",
            key="posts_text",
            height=320,
            placeholder="First job post...\n---\nSecond job post...\n---\nThird job post...",
            help="Put a line with three dashes (---) between two job posts.",
        )
        return split_job_posts(st.session_state.posts_text)

    posts = []
    for number, post_id in enumerate(st.session_state.post_ids, start=1):
        label_col, button_col = st.columns([5, 1], vertical_alignment="bottom")
        label_col.markdown(f"**Job post #{number}**")
        button_col.button(
            "Remove", key=f"remove_{post_id}", icon=":material/close:",
            on_click=remove_post_field, args=(post_id,), width="stretch",
        )
        text = st.text_area(
            f"Job post #{number}", key=f"post_{post_id}", height=160, label_visibility="collapsed"
        )
        if text.strip():
            posts.append(text.strip())
    st.button("Add job post", icon=":material/add:", on_click=add_post_field)
    return posts


def skill_badges(rows, color: str, icon: str) -> str:
    """Markdown badges like ':green-badge[:material/check: SQL · 3]'."""
    return " ".join(
        f":{color}-badge[:material/{icon}: {row.skill} · {row.posts_count}]"
        for row in rows.itertuples()
    )


def render_results(cv_text: str, posts: list[str], dictionary: SkillDictionary) -> None:
    posts_skills = find_skills_in_posts(posts, dictionary)
    cv_skills = find_skills(cv_text, dictionary)
    table = build_skill_table(posts_skills, cv_skills, dictionary)

    if table.empty:
        st.warning(
            ":material/search_off: No known skills were found in the job posts. "
            "Check that you pasted the full text, or extend data/skills.yaml."
        )
        return

    score = coverage_score(table)
    n_posts = len(posts)
    n_covered = int(table["in_cv"].sum())
    mode = "dark" if st.context.theme.type == "dark" else "light"

    # --- Headline numbers ---------------------------------------------------
    st.header("Results")
    kpi = st.columns(4)
    kpi[0].metric("Weighted coverage", f"{score:.0f}%",
                  help="Requested skills found in your CV, weighted by how many posts ask for each one.")
    kpi[1].metric("Job posts analysed", n_posts)
    kpi[2].metric("Skills in your CV", f"{n_covered} of {len(table)}")
    kpi[3].metric("Missing skills", len(table) - n_covered)
    st.progress(score / 100)

    # --- Demand chart --------------------------------------------------------
    st.subheader(":material/bar_chart: Most requested skills")
    controls = st.columns([2, 2, 3], vertical_alignment="bottom")
    max_bars = len(table)
    top_n = controls[0].slider("Skills to show", 1, max_bars, min(20, max_bars)) if max_bars > 1 else 1
    group = controls[1].toggle("Group by category", value=True)
    shown = table.head(top_n)
    st.plotly_chart(
        demand_bar_chart(shown, dictionary.categories, n_posts, group_by_category=group, mode=mode),
        width="stretch",
        config={"displayModeBar": False},
    )

    # --- CV comparison -------------------------------------------------------
    st.subheader(":material/compare_arrows: Your CV vs the market")
    st.caption("The number next to each skill is how many job posts ask for it.")
    present = table[table["in_cv"]]
    missing = table[~table["in_cv"]]
    col_present, col_missing = st.columns(2)
    with col_present:
        st.markdown(f"**:material/check_circle: In your CV ({len(present)})**")
        st.markdown(skill_badges(present, "green", "check") if not present.empty else "_None yet._")
    with col_missing:
        st.markdown(f"**:material/cancel: Missing from your CV ({len(missing)})**")
        st.markdown(skill_badges(missing, "red", "close") if not missing.empty else "_Nothing missing!_")

    extras = extra_cv_skills(table, cv_skills)
    if extras:
        st.caption("Also in your CV but not requested by these posts: " + ", ".join(extras))

    # --- Study priorities and category coverage -----------------------------
    col_priorities, col_categories = st.columns([3, 2], gap="large")
    with col_priorities:
        st.subheader(f":material/school: Top {TOP_PRIORITIES} study priorities")
        priorities = study_priorities(table, TOP_PRIORITIES)
        if priorities.empty:
            st.success("Your CV covers every requested skill. Well done!")
        else:
            priorities = priorities.assign(
                rank=range(1, len(priorities) + 1), share=priorities["posts_share"] * 100
            )
            st.dataframe(
                priorities[["rank", "skill", "category", "posts_count", "share"]],
                hide_index=True,
                width="stretch",
                column_config={
                    "rank": st.column_config.NumberColumn("#", width=40),
                    "skill": "Skill",
                    "category": "Category",
                    "posts_count": st.column_config.NumberColumn("Posts", width=60),
                    "share": st.column_config.ProgressColumn(
                        "Share of posts", format="%.0f%%", min_value=0, max_value=100,
                        width="small",
                    ),
                },
            )
    with col_categories:
        st.subheader(":material/category: Coverage by category")
        st.plotly_chart(
            category_coverage_chart(category_breakdown(table, dictionary), mode=mode),
            width="stretch",
            config={"displayModeBar": False},
        )

    # --- Full table ----------------------------------------------------------
    with st.expander("Full skill table"):
        export = table.assign(posts_share=(table["posts_share"] * 100).round(1))
        st.dataframe(export, hide_index=True, width="stretch")
        st.download_button(
            "Download as CSV",
            export.to_csv(index=False).encode("utf-8"),
            file_name="skill_gap_analysis.csv",
            mime="text/csv",
            icon=":material/download:",
            help="The file is generated in your browser session and not stored on the server.",
        )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def main() -> None:
    init_state()
    try:
        dictionary = get_dictionary()
    except DictionaryError as exc:
        st.error(f"The skill dictionary could not be loaded: {exc}")
        st.stop()

    render_sidebar(dictionary)

    st.title("Skill Gap Analyzer")
    st.badge(f"Alpha · v{__version__}", icon=":material/science:", color="orange")
    st.caption(
        "Early version: skill detection is dictionary-based and still being tuned on "
        f"real job posts. Spotted a wrong or missing skill? [Open an issue]({ISSUES_URL})."
    )
    st.markdown(
        "Find out which skills the job market asks for in **Data Analyst, BI Analyst "
        "and Business Analyst** roles, and which ones are missing from your CV."
    )
    st.info(
        "**Privacy:** nothing is saved. Your CV and the job posts stay in memory only "
        "for this session and are discarded when you close the page.",
        icon=":material/lock:",
    )

    buttons = st.columns([3, 2, 7])
    buttons[0].button("Load sample data", icon=":material/science:", on_click=load_sample_data,
                      width="stretch")
    buttons[1].button("Clear all", icon=":material/delete:", on_click=clear_all,
                      width="stretch")

    col_cv, col_posts = st.columns([2, 3], gap="large")
    with col_cv:
        cv_text = render_cv_input()
    with col_posts:
        posts = render_posts_input()

    st.divider()
    if not posts:
        st.markdown(":material/arrow_upward: Add at least one job post to see the analysis.")
        return
    if not cv_text.strip():
        st.markdown(
            ":material/arrow_upward: Upload your CV (or paste its text) to compare it "
            "with the market. Meanwhile, here is what the job posts ask for."
        )
    render_results(cv_text, posts, dictionary)


main()
