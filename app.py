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
    split_soft_skills,
    study_priorities,
)
from skill_gap.charts import category_coverage_chart, coverage_donut, demand_bar_chart
from skill_gap.extractor import (
    REQUIRED,
    SkillMention,
    find_skill_mentions,
    find_skills_in_posts,
    post_title,
    split_job_posts,
)
from skill_gap.pdf_reader import PdfReadError, extract_text_from_pdf
from skill_gap.report import build_pdf_report
from skill_gap.skills_dictionary import (
    DictionaryError,
    SkillDictionary,
    list_dictionaries,
    load_dictionary,
)

SAMPLES_DIR = Path(__file__).resolve().parent / "data" / "samples"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
MODE_SINGLE_BOX = "One text box (separate posts with ---)"
MODE_FIELDS = "One field per job post"
TOP_PRIORITIES = 5
ISSUES_URL = "https://github.com/v-ambrosino/skill-gap-analyzer/issues"

st.set_page_config(
    page_title="Skill Gap Analyzer",
    page_icon=str(ASSETS_DIR / "logo.svg"),
    layout="wide",
    menu_items={
        "Report a bug": ISSUES_URL,
        "About": "Skill Gap Analyzer: compare your CV with real job posts. No AI, nothing stored.",
    },
)


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
    st.session_state.analyzed = True


def clear_all() -> None:
    for post_id in st.session_state.post_ids:
        st.session_state.pop(f"post_{post_id}", None)
    st.session_state.post_ids = [0]
    st.session_state.next_post_id = 1
    st.session_state.posts_text = ""
    st.session_state.cv_text_manual = ""
    # Changing the uploader key is the way to reset a st.file_uploader.
    st.session_state.uploader_key = st.session_state.get("uploader_key", 0) + 1
    st.session_state.analyzed = False


# ---------------------------------------------------------------------------
# Look and feel
# ---------------------------------------------------------------------------
LANGUAGES = "English, Italian, French, German, Spanish and Portuguese"

# A little CSS on top of the theme in .streamlit/config.toml: the hero band and
# the step cards. Colours are fixed on the hero (white on blue), so it reads the
# same in light and dark mode.
_CSS = """
<style>
.sga-hero {
  background: linear-gradient(120deg, #1c5cab 0%, #2a78d6 55%, #5b8def 100%);
  border-radius: 20px; padding: 36px 40px 30px; color: #ffffff; margin-bottom: 8px;
}
.sga-hero h1 { color: #ffffff; font-size: 2.6rem; line-height: 1.15; margin: 0 0 10px; padding: 0; }
.sga-hero p { color: #e8f0fd; font-size: 1.1rem; margin: 0 0 18px; max-width: 760px; }
.sga-chip {
  display: inline-block; background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.35);
  color: #ffffff; border-radius: 999px; padding: 4px 12px; margin: 0 6px 6px 0; font-size: 0.85rem;
}
.sga-step-number {
  display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px;
  border-radius: 50%; background: #2a78d6; color: #ffffff; font-weight: 700; margin-bottom: 6px;
}
@media (max-width: 640px) {
  .sga-hero { padding: 24px 20px 18px; }
  .sga-hero h1 { font-size: 1.9rem; }
}
</style>
"""


def render_hero(dictionary: SkillDictionary, role: str) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="sga-hero">
  <h1>Find your skill gap in 30 seconds</h1>
  <p>Upload your CV, paste a few job posts for <b>{dictionary.description or role}</b>
  and see which skills the market asks for, which ones you are missing and what to study first.</p>
  <span class="sga-chip">No AI, explainable results</span>
  <span class="sga-chip">Private: nothing is stored</span>
  <span class="sga-chip">6 European languages</span>
  <span class="sga-chip">PDF report</span>
</div>
""",
        unsafe_allow_html=True,
    )


def render_steps() -> None:
    steps = [
        ("1", "Upload your CV", "A text-based PDF, or paste its text."),
        ("2", "Paste job posts", f"One or more posts, in {LANGUAGES}."),
        ("3", "Get your gap", "Coverage, priorities, evidence and a PDF report."),
    ]
    for column, (number, title, text) in zip(st.columns(3), steps):
        with column.container(border=True):
            st.markdown(f'<span class="sga-step-number">{number}</span>', unsafe_allow_html=True)
            st.markdown(f"**{title}**  \n{text}")


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
                "nice to have (\"is a plus\", \"gradita\", \"von Vorteil\", \"se valorará\") "
                "counts this much. 0 ignores nice-to-have skills, 1 treats them as requirements."
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
        st.caption(
            "The online version runs on Streamlit Community Cloud: files are processed in "
            "that server's memory and never stored. For full control, run the app locally "
            "(see the README)."
        )
        st.divider()
        st.header(":material/help: How it works")
        st.markdown(
            "1. Skills are recognised with an editable **dictionary** "
            f"of **{len(dictionary.skills)} skills**, with synonyms in {LANGUAGES}.\n"
            "2. Each skill counts **once per job post**: 1 if the post **requires** it, "
            "less if it is only **nice to have** (see Settings).\n"
            "3. **Coverage** = share of the requested technical skills found in your CV, "
            "weighted by that demand."
        )
        st.caption(
            f"v{__version__} · [Source code](https://github.com/v-ambrosino/skill-gap-analyzer) · "
            f"[Report an issue]({ISSUES_URL})"
        )
    return nice_weight


def render_cv_input() -> str:
    """Return the CV text, from the uploaded PDF or from the text box."""
    st.markdown("#### :material/description: Your CV")
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
    st.markdown("#### :material/work: Job posts")
    mode = st.radio("Input mode", [MODE_SINGLE_BOX, MODE_FIELDS], horizontal=True, key="input_mode")

    if mode == MODE_SINGLE_BOX:
        st.text_area(
            "Paste one or more job posts",
            key="posts_text",
            height=300,
            placeholder="First job post...\n---\nSecond job post...\n---\nThird job post...",
            help=f"Put a line with three dashes (---) between two job posts. Languages: {LANGUAGES}.",
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


def render_evidence(
    table,
    posts: list[str],
    posts_mentions: list[dict[str, SkillMention]],
    cv_mentions: dict[str, SkillMention],
) -> None:
    """Show the sentences where a chosen skill was found, to check the matching."""
    st.markdown("#### :material/format_quote: Where each skill was found")
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


def render_soft_skills(soft) -> None:
    """Soft skills the posts ask for, split into missing and already visible."""
    if soft.empty:
        return
    missing = soft[~soft["in_cv"]]
    present = soft[soft["in_cv"]]
    with st.container(border=True):
        st.markdown("#### :material/record_voice_over: Soft skills to make visible in your CV")
        if missing.empty:
            st.success("Every soft skill the posts ask for is already visible in your CV.")
        else:
            st.caption(
                "Employers ask for these soft skills, but your CV does not mention them in words "
                "the app recognises. They are not counted in the coverage score: rather than "
                "studying them, show them with a concrete example, e.g. \"presented monthly "
                "results to the sales team\" for communication."
            )
            st.markdown(skill_badges(missing, "orange", "visibility"))
        if not present.empty:
            st.caption("Already visible in your CV: " + ", ".join(present["skill"]))


def render_priorities(technical) -> None:
    st.markdown(f"#### :material/school: Top {TOP_PRIORITIES} study priorities")
    priorities = study_priorities(technical, TOP_PRIORITIES)
    if priorities.empty:
        st.success("Your CV covers every requested technical skill. Well done!")
        return
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

    # Soft skills get their own section: the score, the missing skills and the
    # study priorities use the technical skills only.
    technical, soft = split_soft_skills(table)
    score = coverage_score(technical)
    if score is None:
        st.warning(
            ":material/info: No technical skills to score: the posts list only soft skills, "
            "or only nice-to-have skills with a weight of 0 (see the sidebar)."
        )
        return
    n_posts = len(posts)
    n_covered = int(technical["in_cv"].sum())
    mode = "dark" if st.context.theme.type == "dark" else "light"
    breakdown = category_breakdown(technical, dictionary)
    extras = extra_cv_skills(table, cv_skills)

    report = build_pdf_report(
        technical,
        soft,
        breakdown,
        study_priorities(technical, TOP_PRIORITIES),
        extras,
        role=dictionary.domain,
        n_posts=n_posts,
        coverage=score,
        nice_weight=nice_weight,
        version=__version__,
    )

    # --- Header row and headline numbers ------------------------------------
    title_col, download_col = st.columns([3, 1], vertical_alignment="bottom")
    title_col.header("Your results")
    download_col.download_button(
        "Download PDF report",
        report,
        file_name="skill_gap_report.pdf",
        mime="application/pdf",
        icon=":material/picture_as_pdf:",
        type="primary",
        width="stretch",
        key="download_top",
    )
    kpi = st.columns(4)
    kpi[0].metric("Weighted coverage", f"{score:.0f}%", border=True,
                  help="Requested technical skills found in your CV, weighted by how many posts ask "
                       "for each one (nice-to-have skills count less, see the sidebar). "
                       "Soft skills are listed separately and not scored.")
    kpi[1].metric("Job posts analysed", n_posts, border=True)
    kpi[2].metric("Technical skills in your CV", f"{n_covered} of {len(technical)}", border=True)
    kpi[3].metric("Missing technical skills", len(technical) - n_covered, border=True)

    overview, skills_tab, evidence_tab, report_tab = st.tabs([
        ":material/dashboard: Overview",
        ":material/bar_chart: Skills",
        ":material/format_quote: Evidence",
        ":material/picture_as_pdf: Report",
    ])

    # --- Overview: score, priorities, soft skills -----------------------------
    with overview:
        col_score, col_priorities = st.columns([1, 2], gap="large")
        with col_score:
            st.plotly_chart(coverage_donut(score, mode), width="stretch",
                            config={"displayModeBar": False})
        with col_priorities:
            render_priorities(technical)
        render_soft_skills(soft)

    # --- Skills: demand chart, CV vs market, categories ---------------------------
    with skills_tab:
        st.markdown("#### :material/bar_chart: Most requested skills")
        controls = st.columns([2, 2, 3], vertical_alignment="bottom")
        max_bars = len(table)
        top_n = controls[0].slider("Skills to show", 1, max_bars, min(20, max_bars)) if max_bars > 1 else 1
        group = controls[1].toggle("Group by category", value=True)
        st.plotly_chart(
            demand_bar_chart(table.head(top_n), dictionary.categories, n_posts,
                             group_by_category=group, mode=mode),
            width="stretch",
            config={"displayModeBar": False},
        )

        st.markdown("#### :material/compare_arrows: Your CV vs the market")
        st.caption("Technical skills. The number next to each skill is how many job posts ask for it.")
        present = technical[technical["in_cv"]]
        missing = technical[~technical["in_cv"]]
        col_present, col_missing = st.columns(2)
        with col_present.container(border=True):
            st.markdown(f"**:material/check_circle: In your CV ({len(present)})**")
            st.markdown(skill_badges(present, "green", "check") if not present.empty else "_None yet._")
        with col_missing.container(border=True):
            st.markdown(f"**:material/cancel: Missing from your CV ({len(missing)})**")
            st.markdown(skill_badges(missing, "red", "close") if not missing.empty else "_Nothing missing!_")
        if extras:
            st.caption("Also in your CV but not requested by these posts: " + ", ".join(extras))

        st.markdown("#### :material/category: Coverage by category")
        st.plotly_chart(category_coverage_chart(breakdown, mode=mode), width="stretch",
                        config={"displayModeBar": False})

        with st.expander("Full skill table"):
            st.dataframe(
                table.assign(posts_share=(table["posts_share"] * 100).round(1)),
                hide_index=True, width="stretch",
            )

    # --- Evidence --------------------------------------------------------------------
    with evidence_tab:
        render_evidence(table, posts, posts_mentions, cv_mentions)

    # --- Report ------------------------------------------------------------------------
    with report_tab:
        st.markdown("#### :material/picture_as_pdf: Your PDF report")
        st.markdown(
            "A ready-to-share summary: coverage, the top study priorities, the most requested "
            "skills, coverage by category, your CV vs the market, the soft skills to show and "
            "the full skill table."
        )
        st.caption(
            "Generated in memory for this session only. It contains skill names and scores, "
            "never the text of your CV or of the job posts."
        )
        st.download_button(
            "Download PDF report",
            report,
            file_name="skill_gap_report.pdf",
            mime="application/pdf",
            icon=":material/download:",
            type="primary",
            key="download_tab",
        )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def start_analysis() -> None:
    st.session_state.analyzed = True


def main() -> None:
    init_state()
    st.session_state.setdefault("analyzed", False)
    st.logo(str(ASSETS_DIR / "logo_wide.svg"), icon_image=str(ASSETS_DIR / "logo.svg"))
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
    render_hero(dictionary, role)

    buttons = st.columns([3, 2, 6])
    buttons[0].button(
        "Try with sample data", icon=":material/science:", on_click=load_sample_data,
        args=(Path(dictionary_files[role]).stem,), type="primary", width="stretch",
        help="Fictional job posts and CV for the selected target role.",
    )
    buttons[1].button("Clear all", icon=":material/delete:", on_click=clear_all, width="stretch")

    render_steps()

    col_cv, col_posts = st.columns([2, 3], gap="large")
    with col_cv.container(border=True):
        cv_text = render_cv_input()
    with col_posts.container(border=True):
        posts = render_posts_input()

    st.button(
        "Analyze my skill gap", icon=":material/insights:", type="primary",
        width="stretch", on_click=start_analysis, disabled=not posts,
        help=None if posts else "Add at least one job post first.",
    )

    if not st.session_state.analyzed or not posts:
        st.caption(
            ":material/lock: Your CV and the job posts stay in memory for this session only "
            "and are discarded when you close the page."
        )
        return
    st.divider()
    if not cv_text.strip():
        st.info(
            "No CV yet: upload it (or paste its text) to compare it with the market. "
            "Meanwhile, here is what the job posts ask for.",
            icon=":material/info:",
        )
    render_results(cv_text, posts, dictionary, nice_weight)


main()
