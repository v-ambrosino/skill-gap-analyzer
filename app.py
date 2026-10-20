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
from skill_gap.resources import load_resources, resources_for
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
    initial_sidebar_state="collapsed",
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
def get_resources() -> dict[str, list[tuple[str, str]]]:
    return load_resources()


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
    st.session_state.scroll_to_results = True
    _load_sample_data(role_folder)


def _load_sample_data(role_folder: str) -> None:
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
REPO_URL = "https://github.com/v-ambrosino/skill-gap-analyzer"

# The page is styled like a product website on top of the theme in
# .streamlit/config.toml: Streamlit's own toolbar is hidden, the content is
# centred, cards get soft shadows, buttons are pills and tabs are a segmented
# control. Only stable `data-testid` hooks are used.
_CSS = """
<style>
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { visibility: hidden; height: 0; }
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1100px 520px at 0% -10%, #dfeafc 0%, rgba(223,234,252,0) 60%),
    radial-gradient(900px 480px at 100% -5%, #ece6fd 0%, rgba(236,230,253,0) 55%),
    #f8fafd;
}
[data-testid="stMainBlockContainer"] { max-width: 1160px; padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="stVerticalBlockBorderWrapper"] {
  background: #ffffff; border: 1px solid #e6eaf1 !important; border-radius: 18px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 10px 28px rgba(16,24,40,.06);
}
[data-testid="stMetric"] {
  background: #ffffff; border-radius: 16px; border: 1px solid #e6eaf1;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 8px 20px rgba(16,24,40,.05);
}
[data-testid="stMetricValue"] { font-weight: 700; color: #14213d; }
[data-testid="stBaseButton-primary"] {
  background: linear-gradient(135deg, #2a78d6 0%, #5b5bd6 100%); border: 0; border-radius: 999px;
  box-shadow: 0 8px 18px rgba(42,120,214,.28); font-weight: 600; transition: transform .15s, filter .15s;
}
[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.07); transform: translateY(-1px); }
[data-testid="stBaseButton-secondary"] { border-radius: 999px; background: #ffffff; }
[role="tablist"] { gap: 4px; background: #eaf0f8; padding: 5px; border-radius: 999px; width: fit-content;
  border: 0 !important; box-shadow: none !important; }
[data-testid="stTab"] { border-radius: 999px; padding: 6px 18px; height: auto; border: 0 !important; }
[data-testid="stTab"][aria-selected="true"] { background: #ffffff; box-shadow: 0 1px 4px rgba(16,24,40,.14); }
[role="tablist"] > :not([role="tab"]) { display: none; }

.sga-nav { display: flex; align-items: center; justify-content: space-between; padding: 6px 2px 18px; }
.sga-brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 1.15rem; color: #14213d; }
.sga-links a { color: #475467; text-decoration: none; margin-left: 22px; font-size: .95rem; font-weight: 500; }
.sga-links a:hover { color: #2a78d6; }
.sga-eyebrow { display: inline-block; background: #e3eefc; color: #1c5cab; border-radius: 999px;
  padding: 4px 12px; font-size: .82rem; font-weight: 600; margin-bottom: 14px; }
.sga-title { font-size: 3.1rem; line-height: 1.08; font-weight: 800; color: #14213d; margin: 0 0 16px;
  letter-spacing: -0.02em; }
.sga-title span { background: linear-gradient(135deg, #2a78d6, #6d4fd8); -webkit-background-clip: text;
  background-clip: text; color: transparent; }
.sga-lead { font-size: 1.12rem; color: #475467; line-height: 1.6; margin: 0 0 18px; max-width: 560px; }
.sga-ghost { display: inline-block; padding: 8px 18px; border-radius: 999px; border: 1px solid #d0d7e2;
  background: #ffffff; color: #14213d !important; text-decoration: none !important; font-weight: 600; font-size: .95rem; }
.sga-ghost:hover { border-color: #2a78d6; color: #2a78d6 !important; }
.sga-checks { color: #475467; font-size: .92rem; margin: 6px 0 0; }
.sga-checks b { color: #0e9f6e; }
.sga-preview { background: #ffffff; border: 1px solid #e6eaf1; border-radius: 22px; padding: 22px 24px;
  box-shadow: 0 24px 60px rgba(28,92,171,.16); }
.sga-preview-head { display: flex; justify-content: space-between; color: #667085; font-size: .82rem; }
.sga-preview-row { display: flex; align-items: center; gap: 20px; margin: 12px 0 14px; }
.sga-preview-kpi { font-size: .85rem; color: #667085; line-height: 1.9; }
.sga-preview-kpi b { color: #14213d; font-size: 1rem; }
.sga-chip { display: inline-block; border-radius: 8px; padding: 3px 9px; margin: 0 5px 6px 0; font-size: .8rem; font-weight: 500; }
.sga-chip.ok { background: #e7f6ec; color: #08663a; }
.sga-chip.miss { background: #fdecec; color: #a32121; }
.sga-section-title { text-align: center; font-size: 2rem; font-weight: 800; color: #14213d; margin: 46px 0 6px;
  letter-spacing: -0.01em; }
.sga-section-lead { text-align: center; color: #667085; margin: 0 auto 22px !important; max-width: 640px; display: block; }
.sga-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
.sga-card { background: #ffffff; border: 1px solid #e6eaf1; border-radius: 18px; padding: 20px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04), 0 10px 28px rgba(16,24,40,.06); }
.sga-card h4 { margin: 12px 0 6px; font-size: 1.02rem; color: #14213d; padding: 0; }
.sga-card p { margin: 0; color: #667085; font-size: .92rem; line-height: 1.5; }
.sga-icon { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center;
  justify-content: center; background: linear-gradient(135deg, #e3eefc, #ece6fd); color: #2a78d6; font-weight: 800; }
.sga-footer { margin-top: 48px; padding: 22px 0 6px; border-top: 1px solid #e6eaf1; display: flex;
  flex-wrap: wrap; justify-content: space-between; gap: 10px; color: #667085; font-size: .88rem; }
.sga-footer a { color: #475467; text-decoration: none; margin-left: 16px; }
@media (max-width: 760px) {
  .sga-title { font-size: 2.2rem; }
  .sga-links a { margin-left: 12px; font-size: .85rem; }
  .sga-links a.hide-sm { display: none; }
}
</style>
"""

_LOGO_SVG = (
    '<svg width="30" height="30" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="14" '
    'fill="#2a78d6"/><rect x="13" y="34" width="9" height="17" rx="3" fill="#fff"/><rect x="27.5" y="24" '
    'width="9" height="27" rx="3" fill="#fff"/><rect x="42" y="13" width="9" height="38" rx="3" fill="#fff" '
    'fill-opacity="0.45"/><path d="M42 13h9v12h-9z" fill="#fff"/></svg>'
)

# A static example card shown in the hero, so visitors see the result at a glance.
_PREVIEW = """
<div class="sga-preview">
  <div class="sga-preview-head"><span>Example result</span><span>12 job posts · Data Analyst</span></div>
  <div class="sga-preview-row">
    <svg width="116" height="116" viewBox="0 0 120 120" aria-label="72% coverage">
      <circle cx="60" cy="60" r="48" fill="none" stroke="#e3eefc" stroke-width="14"/>
      <circle cx="60" cy="60" r="48" fill="none" stroke="url(#g)" stroke-width="14" stroke-linecap="round"
        stroke-dasharray="217 302" transform="rotate(-90 60 60)"/>
      <defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#2a78d6"/><stop offset="1" stop-color="#6d4fd8"/></linearGradient></defs>
      <text x="60" y="66" text-anchor="middle" font-size="24" font-weight="800" fill="#14213d">72%</text>
    </svg>
    <div class="sga-preview-kpi"><b>18 of 25</b> skills in your CV<br><b>3</b> study priorities<br><b>PDF</b> report ready</div>
  </div>
  <div><span class="sga-chip ok">✓ SQL · 11</span><span class="sga-chip ok">✓ Power BI · 8</span><span class="sga-chip ok">✓ Python · 7</span>
  <span class="sga-chip miss">✕ Tableau · 5</span><span class="sga-chip miss">✕ dbt · 3</span><span class="sga-chip miss">✕ A/B Testing · 2</span></div>
</div>
"""

_FEATURES = [
    ("✓", "Explainable, no AI", "Every skill comes from a dictionary rule, and the app shows the exact sentence that matched."),
    ("⚖", "Weighted by demand", "Skills that most employers require count more; nice-to-have skills count half."),
    ("🌍", "6 European languages", f"Job posts in {LANGUAGES}."),
    ("🔒", "Private by design", "Your CV is processed in memory for this session only and never stored."),
]
_STEPS = [
    ("1", "Upload your CV", "A text-based PDF, or paste its text."),
    ("2", "Paste job posts", "One or more posts, separated by a line with ---."),
    ("3", "Get your gap", "Coverage, study priorities, the evidence and a PDF report."),
]


def render_header() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="sga-nav">
  <div class="sga-brand">{_LOGO_SVG}<span>Skill Gap Analyzer</span></div>
  <div class="sga-links"><a href="#how-it-works" class="hide-sm">How it works</a>
  <a href="#analyze">Try it</a><a href="{REPO_URL}" target="_blank">GitHub</a></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_hero(dictionary: SkillDictionary, role: str, sample_folder: str) -> None:
    text_col, preview_col = st.columns([1.15, 1], gap="large", vertical_alignment="center")
    with text_col:
        st.markdown(
            f"""
<div class="sga-eyebrow">Free · open source · v{__version__}</div>
<h1 class="sga-title">Find your <span>skill gap</span> in 30 seconds</h1>
<p class="sga-lead">Compare your CV with real job posts for <b>{dictionary.description or role}</b>:
see which skills employers ask for, which ones you are missing and what to study first.</p>
""",
            unsafe_allow_html=True,
        )
        buttons = st.columns([1.3, 1, 0.4], vertical_alignment="center")
        buttons[0].button(
            "Try with sample data", icon=":material/play_arrow:", on_click=load_sample_data,
            args=(sample_folder,), type="primary", width="stretch",
            help="Fictional job posts and CV for the selected target role.",
        )
        buttons[1].markdown('<a class="sga-ghost" href="#how-it-works">How it works →</a>',
                            unsafe_allow_html=True)
        st.markdown(
            '<p class="sga-checks"><b>✓</b> No sign-up &nbsp; <b>✓</b> Nothing stored &nbsp; <b>✓</b> PDF report</p>',
            unsafe_allow_html=True,
        )
    with preview_col:
        st.markdown(_PREVIEW, unsafe_allow_html=True)


def render_features() -> None:
    cards = "".join(
        f'<div class="sga-card"><div class="sga-icon">{icon}</div><h4>{title}</h4><p>{text}</p></div>'
        for icon, title, text in _FEATURES
    )
    steps = "".join(
        f'<div class="sga-card"><div class="sga-icon">{number}</div><h4>{title}</h4><p>{text}</p></div>'
        for number, title, text in _STEPS
    )
    st.markdown(
        f"""
<div class="sga-section-title">Why Skill Gap Analyzer</div>
<p class="sga-section-lead">A transparent way to read the job market, built for Data Analyst, BI and Data Engineer roles.</p>
<div class="sga-grid">{cards}</div>
<div class="sga-section-title" id="how-it-works">How it works</div>
<p class="sga-section-lead">Three steps, about a minute, no account needed.</p>
<div class="sga-grid">{steps}</div>
<div class="sga-section-title" id="analyze">Analyze your CV</div>
<p class="sga-section-lead">Choose the role, add your CV and the job posts, then click Analyze.</p>
""",
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        f"""
<div class="sga-footer">
  <span>Skill Gap Analyzer v{__version__} · No AI, nothing stored · Made with Python and Streamlit</span>
  <span><a href="{REPO_URL}" target="_blank">Source code</a><a href="{ISSUES_URL}" target="_blank">Report an issue</a></span>
</div>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# UI building blocks
# ---------------------------------------------------------------------------
def render_sidebar(dictionary: SkillDictionary) -> None:
    """The sidebar (collapsed at start): privacy and how the score works."""
    with st.sidebar:
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
    resources = get_resources()
    priorities = priorities.assign(
        rank=range(1, len(priorities) + 1),
        share=priorities["posts_share"] * 100,
        learn=[resources_for(skill, resources)[0][1] for skill in priorities["skill"]],
    )
    st.dataframe(
        priorities[["rank", "skill", "category", "required_count", "nice_count", "share", "learn"]],
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
            "learn": st.column_config.LinkColumn(
                "Learn it", display_text="Free resource ↗", width=130,
                help="A free place to start learning the skill",
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
        resources=get_resources(),
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
    st.session_state.scroll_to_results = True


def scroll_to_results() -> None:
    """Bring the results into view after Analyze or Try with sample data."""
    if not st.session_state.pop("scroll_to_results", False):
        return
    script = (
        "<script>const el = window.parent.document.getElementById('your-results');"
        "if (el) { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }</script>"
    )
    if hasattr(st, "iframe"):  # Streamlit 1.5x+
        st.iframe(script, height=1)
    else:  # older Streamlit versions
        import streamlit.components.v1 as components

        components.html(script, height=0)


def main() -> None:
    init_state()
    st.session_state.setdefault("analyzed", False)
    st.logo(str(ASSETS_DIR / "logo_wide.svg"), icon_image=str(ASSETS_DIR / "logo.svg"))
    try:
        dictionary_files = get_dictionary_files()
        role = st.session_state.get("role") or next(iter(dictionary_files))
        dictionary = get_dictionary(dictionary_files[role])
    except DictionaryError as exc:
        st.error(f"The skill dictionary could not be loaded: {exc}")
        st.stop()
    sample_folder = Path(dictionary_files[role]).stem

    render_sidebar(dictionary)
    render_header()
    render_hero(dictionary, role, sample_folder)
    render_features()

    # --- The analyser ---------------------------------------------------------
    with st.container(border=True):
        col_role, col_weight, col_clear = st.columns([2, 2, 1], vertical_alignment="bottom")
        col_role.selectbox(
            ":material/work: Target role", list(dictionary_files), key="role",
            help="Each role has its own skill dictionary in data/dictionaries/.",
        )
        with col_weight.popover("Advanced settings", icon=":material/tune:", width="stretch"):
            nice_weight = st.select_slider(
                "Weight of nice-to-have skills",
                options=[0.0, 0.25, 0.5, 0.75, 1.0],
                value=DEFAULT_NICE_WEIGHT,
                format_func=lambda w: f"{w:g}",
                key="nice_weight",
                help=(
                    "A post that requires a skill counts 1. A post where the skill is only "
                    "nice to have (\"is a plus\", \"gradita\", \"von Vorteil\", \"se valorará\") "
                    "counts this much. 0 ignores nice-to-have skills, 1 treats them as requirements."
                ),
            )
        col_clear.button("Clear all", icon=":material/delete:", on_click=clear_all, width="stretch")

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

    if st.session_state.analyzed and posts:
        st.markdown('<div id="your-results"></div>', unsafe_allow_html=True)
        if not cv_text.strip():
            st.info(
                "No CV yet: upload it (or paste its text) to compare it with the market. "
                "Meanwhile, here is what the job posts ask for.",
                icon=":material/info:",
            )
        render_results(cv_text, posts, dictionary, nice_weight)
        scroll_to_results()
    else:
        st.caption(
            ":material/lock: Your CV and the job posts stay in memory for this session only "
            "and are discarded when you close the page."
        )
    render_footer()


main()
