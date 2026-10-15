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
    DEFAULT_NICE_WEIGHT,
    build_skill_table,
    category_breakdown,
    coverage_score,
    extra_cv_skills,
    study_priorities,
)
from skill_gap.charts import category_coverage_chart, demand_bar_chart
from skill_gap.extractor import (
    REQUIRED,
    SkillMention,
    find_skill_mentions,
    find_skills_in_posts,
    split_job_posts,
)
from skill_gap.pdf_reader import PdfReadError, extract_text_from_pdf
from skill_gap.report import build_html_report
from skill_gap.skills_dictionary import (
    DictionaryError,
    SkillDictionary,
    list_dictionaries,
    load_dictionary,
)

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
def get_dictionary(path: str) -> SkillDictionary:
    """Load a skill dictionary once per server process.

    Only the dictionaries are cached. The CV and the job posts are NEVER
    cached, so they cannot leak between users or outlive the session.
    """
    return load_dictionary(path)


@st.cache_resource
def get_dictionary_files() -> dict[str, str]:
    """Role name -> dictionary file, for every file in data/dictionaries/."""
    return {role: str(path) for role, path in list_dictionaries().items()}


def read_sample(role_folder: str, name: str) -> str:
    """Read a fictional sample file for a role (data/samples/<dictionary name>/)."""
    return (SAMPLES_DIR / role_folder / name).read_text(encoding="utf-8")


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


def load_sample_data(role_folder: str) -> None:
    """Fill both input modes and the CV text box with the fictional samples."""
    clear_all()
    sample_posts = read_sample(role_folder, "job_posts.txt")
    st.session_state.posts_text = sample_posts
    posts = split_job_posts(sample_posts)
    st.session_state.post_ids = list(range(len(posts)))
    st.session_state.next_post_id = len(posts)
    for post_id, post in enumerate(posts):
        st.session_state[f"post_{post_id}"] = post
    st.session_state.cv_text_manual = read_sample(role_folder, "cv.txt")


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
def render_sidebar(dictionary: SkillDictionary) -> float:
    """Draw the sidebar and return the chosen weight of nice-to-have skills."""
    with st.sidebar:
        st.header(":material/tune: Settings")
        nice_weight = st.select_slider(
            "Weight of nice-to-have skills",
            options=[0.0, 0.25, 0.5, 0.75, 1.0],
            value=DEFAULT_NICE_WEIGHT,
            format_func=lambda w: f"{w:g}",
            help=(
                "A post that requires a skill counts 1. A post where the skill is only "
                "nice to have (\"is a plus\", \"gradita\", \"Nice to have:\") counts this much. "
                "0 ignores nice-to-have skills, 1 treats them as requirements."
            ),
        )
        st.divider()
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
            "2. Each skill counts **once per job post**: 1 if the post **requires** it, "
            "less if it is only **nice to have** (see Settings).\n"
            "3. **Coverage** = share of the requested skills found in your CV, "
            "weighted by that demand."
        )
        st.caption("Categories: " + ", ".join(dictionary.categories))
    return nice_weight


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


def post_title(post: str, number: int) -> str:
    """'Post #2 · Data Analyst - Acme' from the first line of the post."""
    first_line = next((line.strip() for line in post.splitlines() if line.strip()), "")
    if len(first_line) > 60:
        first_line = first_line[:59].rstrip() + "\u2026"
    return f"Post #{number} · {first_line}" if first_line else f"Post #{number}"


def render_evidence(
    table,
    posts: list[str],
    posts_mentions: list[dict[str, SkillMention]],
    cv_mentions: dict[str, SkillMention],
) -> None:
    """Show the sentences where a chosen skill was found, to check the matching."""
    st.subheader(":material/format_quote: Where each skill was found")
    st.caption(
        "Pick a skill to see the exact sentences that matched. Useful to check "
        "the result, and to spot wrong matches to report."
    )
    skill = st.selectbox("Skill", table["skill"], label_visibility="collapsed")
    col_posts, col_cv = st.columns([3, 2], gap="large")
    with col_posts:
        st.markdown("**In the job posts**")
        for number, (post, mentions) in enumerate(zip(posts, posts_mentions), start=1):
            mention = mentions.get(skill)
            if mention is None:
                continue
            if mention.priority == REQUIRED:
                tag = ":blue-badge[Required]"
            else:
                tag = ":gray-badge[Nice to have]"
            quote = f"“{mention.snippet}”" if mention.snippet else "_(phrase split across lines)_"
            st.markdown(f"{tag} **{post_title(post, number)}**  \n{quote}")
    with col_cv:
        st.markdown("**In your CV**")
        mention = cv_mentions.get(skill)
        if mention is None:
            st.markdown("_Not found in your CV._")
        else:
            st.markdown(f"“{mention.snippet}”" if mention.snippet else "_Found (phrase split across lines)._")


def render_results(
    cv_text: str, posts: list[str], dictionary: SkillDictionary, nice_weight: float
) -> None:
    posts_mentions = find_skills_in_posts(posts, dictionary)
    cv_mentions = find_skill_mentions(cv_text, dictionary)
    cv_skills = set(cv_mentions)
    table = build_skill_table(posts_mentions, cv_skills, dictionary, nice_weight=nice_weight)

    if table.empty:
        st.warning(
            ":material/search_off: No known skills were found in the job posts. "
            "Check that you pasted the full text, pick another target role in the sidebar, "
            "or extend the dictionaries in data/dictionaries/."
        )
        return

    score = coverage_score(table)
    if score is None:
        st.warning(
            ":material/info: The posts only list nice-to-have skills and their weight is 0. "
            "Raise the weight in the sidebar to include them."
        )
        return
    n_posts = len(posts)
    n_covered = int(table["in_cv"].sum())
    mode = "dark" if st.context.theme.type == "dark" else "light"

    # --- Headline numbers ---------------------------------------------------
    st.header("Results")
    kpi = st.columns(4)
    kpi[0].metric("Weighted coverage", f"{score:.0f}%",
                  help="Requested skills found in your CV, weighted by how many posts ask for each one "
                       "(nice-to-have skills count less, see the sidebar).")
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
                priorities[["rank", "skill", "category", "required_count", "nice_count", "share"]],
                hide_index=True,
                width="stretch",
                column_config={
                    "rank": st.column_config.NumberColumn("#", width=40),
                    "skill": "Skill",
                    "category": "Category",
                    "required_count": st.column_config.NumberColumn(
                        "Required", width=70, help="Posts that require the skill"
                    ),
                    "nice_count": st.column_config.NumberColumn(
                        "Nice", width=60, help="Posts where the skill is nice to have"
                    ),
                    "share": st.column_config.NumberColumn(
                        "Share", format="%.0f%%", width=70,
                        help="Share of the job posts that mention the skill",
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

    render_evidence(table, posts, posts_mentions, cv_mentions)

    # --- Full table and downloads -------------------------------------------
    export = table.assign(posts_share=(table["posts_share"] * 100).round(1))
    with st.expander("Full skill table"):
        st.dataframe(export, hide_index=True, width="stretch")

    st.subheader(":material/download: Download your results")
    st.caption(
        "Files are generated in memory for this session only. The report contains skill "
        "names and scores, never the text of your CV or of the job posts."
    )
    report = build_html_report(
        table,
        category_breakdown(table, dictionary),
        study_priorities(table, TOP_PRIORITIES),
        extras,
        role=dictionary.domain,
        n_posts=n_posts,
        coverage=score,
        nice_weight=nice_weight,
        version=__version__,
    )
    col_report, col_csv, _ = st.columns([2, 2, 3])
    col_report.download_button(
        "Report (HTML)",
        report.encode("utf-8"),
        file_name="skill_gap_report.html",
        mime="text/html",
        icon=":material/description:",
        width="stretch",
        help="Open it in a browser; use Print > Save as PDF to get a PDF.",
    )
    col_csv.download_button(
        "Skill table (CSV)",
        export.to_csv(index=False).encode("utf-8"),
        file_name="skill_gap_analysis.csv",
        mime="text/csv",
        icon=":material/table:",
        width="stretch",
        help="The full skill table, to open in Excel or pandas.",
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def main() -> None:
    init_state()
    try:
        dictionary_files = get_dictionary_files()
        with st.sidebar:
            role = st.selectbox(
                ":material/work: Target role",
                list(dictionary_files),
                help="Each role has its own skill dictionary in data/dictionaries/.",
            )
        dictionary = get_dictionary(dictionary_files[role])
    except DictionaryError as exc:
        st.error(f"The skill dictionary could not be loaded: {exc}")
        st.stop()

    nice_weight = render_sidebar(dictionary)

    st.title("Skill Gap Analyzer")
    st.badge(f"Alpha · v{__version__}", icon=":material/science:", color="orange")
    st.caption(
        "Early version: skill detection is dictionary-based and still being tuned on "
        f"real job posts. Spotted a wrong or missing skill? [Open an issue]({ISSUES_URL})."
    )
    st.markdown(
        f"Find out which skills the job market asks for in **{dictionary.description or role}**, "
        "and which ones are missing from your CV. Change the target role in the sidebar."
    )
    st.info(
        "**Privacy:** nothing is saved. Your CV and the job posts stay in memory only "
        "for this session and are discarded when you close the page.",
        icon=":material/lock:",
    )

    buttons = st.columns([3, 2, 7])
    buttons[0].button("Load sample data", icon=":material/science:", on_click=load_sample_data,
                      args=(Path(dictionary_files[role]).stem,),
                      help="Fictional job posts and CV for the selected target role.",
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
    render_results(cv_text, posts, dictionary, nice_weight)


main()
