"""Skill Gap Analyzer: Streamlit user interface.

Run locally with:  streamlit run app.py

This file only handles layout, user input and session state. All the logic
lives in the `skill_gap` package:
    pdf_reader -> extractor -> analysis -> charts
"""

from __future__ import annotations

import html
from dataclasses import replace
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
from skill_gap.charts import category_coverage_chart, demand_bar_chart
from skill_gap.extractor import (
    REQUIRED,
    SkillMention,
    find_skill_mentions,
    find_skills_in_posts,
    post_title,
    split_job_posts,
)
from skill_gap.keywords import add_custom_skills, merge_dictionaries, suggest_terms
from skill_gap.pdf_reader import PdfReadError, extract_text_from_pdf
from skill_gap.report import build_pdf_report
from skill_gap.resources import load_cv_phrases, load_resources, resources_for
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
AUTHOR = "Vincenzo Ambrosino"
AUTHOR_URL = "https://github.com/v-ambrosino"
LINKEDIN_URL = "https://www.linkedin.com/in/vincenzo-ambrosino/"

st.set_page_config(
    page_title="Skill Gap Analyzer",
    page_icon=str(ASSETS_DIR / "logo.svg"),
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "About": "Skill Gap Analyzer: compare your CV with real job posts. No AI, nothing stored. "
        "© 2026 Vincenzo Ambrosino. All rights reserved.",
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
def get_cv_phrases() -> dict[str, list[str]]:
    return load_cv_phrases()


@st.cache_resource
def get_dictionary_files() -> dict[str, str]:
    """Role name -> dictionary file, for every file in data/dictionaries/."""
    return {role: str(path) for role, path in list_dictionaries().items()}


def known_skills_label() -> str:
    """The number of distinct known skills, rounded down: "300+"."""
    count = len(get_all_skills().skills)
    return f"{count // 50 * 50}+" if count >= 100 else str(count)


@st.cache_resource
def get_all_skills() -> SkillDictionary:
    """Every skill of every dictionary: the starting point for a role typed by the user."""
    return merge_dictionaries([get_dictionary(p) for p in get_dictionary_files().values()], "")


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
    if not role_folder or not (SAMPLES_DIR / role_folder).is_dir():
        # Samples exist for some roles only: show the default role's ones.
        st.session_state.role = next(iter(get_dictionary_files()))
        role_folder = Path(get_dictionary_files()[st.session_state.role]).stem
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

# The page is styled like a product website on top of the theme in
# .streamlit/config.toml: Streamlit's own toolbar is hidden, the content is
# centred, cards get soft layered shadows, buttons are pills and tabs are a
# segmented control. Only stable `data-testid` / `st-key-*` hooks are used.
_CSS = """
<style>
:root {
  --ink: #0b1430; --ink-2: #344054; --muted: #667085; --line: #e7eaf3; --surface: #ffffff;
  --brand: #2f6fe4; --brand-2: #7048e8; --brand-soft: #eef3ff; --ok: #0e9f6e; --bad: #d92d20;
  --grad: linear-gradient(135deg, #2f6fe4 0%, #5a55e6 55%, #7048e8 100%);
  --shadow-sm: 0 1px 2px rgba(16,24,40,.05);
  --shadow: 0 1px 2px rgba(16,24,40,.04), 0 4px 10px rgba(16,24,40,.04), 0 18px 40px rgba(16,24,40,.06);
  --shadow-lg: 0 2px 6px rgba(16,24,40,.05), 0 30px 70px rgba(47,111,228,.18);
}

/* --- Page --------------------------------------------------------------------------- */
[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { visibility: hidden; height: 0; }
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(900px 520px at 8% -8%, rgba(47,111,228,.16), transparent 62%),
    radial-gradient(800px 480px at 95% 0%, rgba(112,72,232,.14), transparent 60%),
    linear-gradient(to bottom, rgba(248,250,253,0) 0, #f8fafd 820px),
    radial-gradient(circle at 1px 1px, rgba(11,20,48,.07) 1px, transparent 0) 0 0 / 24px 24px,
    #f8fafd;
}
[data-testid="stMainBlockContainer"] { max-width: 1180px; padding-top: .6rem; padding-bottom: 2rem; }
h1, h2, h3, h4 { color: var(--ink); letter-spacing: -.015em; }
::selection { background: rgba(47,111,228,.18); }

/* --- Streamlit widgets -------------------------------------------------------------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surface); border: 1px solid var(--line) !important; border-radius: 20px; box-shadow: var(--shadow);
}
[data-testid="stMetric"] {
  position: relative; overflow: hidden; background: var(--surface); border-radius: 18px;
  border: 1px solid var(--line); box-shadow: var(--shadow); padding: 18px 20px 16px !important;
}
[data-testid="stMetric"]::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 3px; background: var(--grad); }
[data-testid="stMetricLabel"] p { text-transform: uppercase; letter-spacing: .06em; font-size: .74rem !important;
  font-weight: 600; color: var(--muted); }
[data-testid="stMetricValue"] { font-weight: 800; color: var(--ink); font-size: 2.1rem; letter-spacing: -.02em; }
[data-testid="stBaseButton-primary"] {
  background: var(--grad); border: 0; border-radius: 999px; font-weight: 600; letter-spacing: .005em;
  box-shadow: 0 1px 0 rgba(255,255,255,.25) inset, 0 8px 20px rgba(47,111,228,.30);
  transition: transform .15s ease, box-shadow .15s ease, filter .15s ease;
}
[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.06); transform: translateY(-1px);
  box-shadow: 0 1px 0 rgba(255,255,255,.25) inset, 0 12px 26px rgba(47,111,228,.36); }
[data-testid="stBaseButton-primary"]:disabled { background: #c9d3e6; box-shadow: none; transform: none; filter: none; }
[data-testid="stBaseButton-secondary"] { border-radius: 999px; background: var(--surface); border-color: var(--line);
  box-shadow: var(--shadow-sm); font-weight: 500; }
[data-testid="stBaseButton-secondary"]:hover { border-color: var(--brand); color: var(--brand); }
.st-key-analyze button { min-height: 3.6rem; font-size: 1.12rem; font-weight: 700; }
.st-key-analyze button p { font-size: 1.12rem; }
[data-testid="stFileUploaderDropzone"] {
  background: linear-gradient(180deg, #f7f9ff, #f1f5ff); border: 1.5px dashed #b8c8ef; border-radius: 16px;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--brand); }
[data-baseweb="textarea"], [data-baseweb="select"] > div, [data-baseweb="input"] {
  border-radius: 12px !important; background: #fbfcff !important; border-color: var(--line) !important;
}
[data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-baseweb="input"]:focus-within {
  border-color: var(--brand) !important; box-shadow: 0 0 0 4px rgba(47,111,228,.12);
}
[data-testid="stExpander"] details { border-radius: 16px; border: 1px solid var(--line); background: var(--surface);
  box-shadow: var(--shadow-sm); }
[data-testid="stExpander"] summary:hover { color: var(--brand); }
[data-testid="stAlert"] { border-radius: 14px; }
[role="tablist"] { gap: 4px; background: #eaeff8; padding: 5px; border-radius: 999px; width: fit-content;
  border: 0 !important; box-shadow: inset 0 1px 2px rgba(16,24,40,.06) !important; }
[data-testid="stTab"] { border-radius: 999px; padding: 7px 18px; height: auto; border: 0 !important; }
[data-testid="stTab"] p { font-weight: 600; }
[data-testid="stTab"][aria-selected="true"] { background: var(--surface); box-shadow: 0 1px 2px rgba(16,24,40,.08), 0 4px 10px rgba(16,24,40,.06); }
[data-testid="stTab"][aria-selected="true"] p { color: var(--brand); }
[role="tablist"] > :not([role="tab"]) { display: none; }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }

/* --- Navigation --------------------------------------------------------------------- */
.sga-nav { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 4px 0 26px;
  padding: 10px 12px 10px 14px; background: rgba(255,255,255,.72); border: 1px solid rgba(231,234,243,.9);
  border-radius: 18px; backdrop-filter: saturate(1.6) blur(12px); -webkit-backdrop-filter: saturate(1.6) blur(12px);
  box-shadow: var(--shadow-sm); }
.sga-brand { display: flex; align-items: center; gap: 10px; font-weight: 750; font-size: 1.08rem; color: var(--ink); }
.sga-version { font-size: .7rem; font-weight: 600; color: var(--brand); background: var(--brand-soft);
  border-radius: 999px; padding: 2px 8px; }
.sga-links { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: .9rem; }
.sga-links .by { margin-right: 6px; }
.sga-links .by b { color: var(--ink); font-weight: 600; }
.sga-links a { display: inline-flex; align-items: center; gap: 6px; color: var(--ink-2) !important;
  text-decoration: none !important; font-weight: 500; padding: 6px 12px; border-radius: 999px;
  border: 1px solid var(--line); background: #fff; transition: border-color .15s, color .15s; }
.sga-links a:hover { border-color: var(--brand); color: var(--brand) !important; }
.sga-links svg { width: 15px; height: 15px; }

/* --- Hero --------------------------------------------------------------------------- */
.sga-eyebrow { display: inline-flex; align-items: center; gap: 8px; background: rgba(255,255,255,.8);
  border: 1px solid var(--line); color: var(--ink-2); border-radius: 999px; padding: 5px 12px 5px 6px;
  font-size: .82rem; font-weight: 500; margin-bottom: 18px; box-shadow: var(--shadow-sm); }
.sga-eyebrow .tag { background: var(--grad); color: #fff; border-radius: 999px; padding: 2px 9px; font-weight: 600; font-size: .74rem; }
.sga-title { font-size: 3.7rem; line-height: 1.02; font-weight: 800; color: var(--ink); margin: 0 0 18px;
  letter-spacing: -0.035em; }
.sga-lead { font-size: 1.16rem; color: var(--ink-2); line-height: 1.62; margin: 0 0 24px; max-width: 540px; }
.sga-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 6px; width: 100%;
  padding: 8px 18px; border-radius: 999px; border: 1px solid var(--line); background: #fff; box-shadow: var(--shadow-sm);
  color: var(--ink) !important; text-decoration: none !important; font-weight: 600; font-size: .95rem; }
.sga-ghost:hover { border-color: var(--brand); color: var(--brand) !important; }
.sga-checks { display: flex; flex-wrap: wrap; gap: 8px 18px; color: var(--ink-2); font-size: .9rem; margin: 14px 0 0; }
.sga-checks span { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.sga-checks svg { width: 16px; height: 16px; color: var(--ok); }

.sga-stage { position: relative; padding: 26px 10px 34px 30px; }
.sga-stage::before { content: ""; position: absolute; inset: 6% 4% 4% 12%; background: var(--grad); filter: blur(60px);
  opacity: .22; border-radius: 40px; z-index: 0; }
.sga-preview { position: relative; z-index: 1; background: rgba(255,255,255,.92); border: 1px solid rgba(231,234,243,.95);
  border-radius: 24px; padding: 22px 24px 46px; box-shadow: var(--shadow-lg); }
.sga-preview-head { display: flex; justify-content: space-between; align-items: center; color: var(--muted); font-size: .8rem; }
.sga-dots { display: inline-flex; gap: 5px; } .sga-dots i { width: 9px; height: 9px; border-radius: 50%; background: #e4e7ef; display: block; }
.sga-preview-row { display: flex; align-items: center; gap: 22px; margin: 14px 0 16px; }
.sga-preview-kpi { display: grid; gap: 8px; font-size: .84rem; color: var(--muted); }
.sga-preview-kpi b { color: var(--ink); font-size: 1.02rem; margin-right: 4px; }
.sga-bars { display: grid; gap: 7px; margin: 4px 0 14px; }
.sga-bar { display: grid; grid-template-columns: 78px 1fr 22px; align-items: center; gap: 10px; font-size: .78rem; color: var(--ink-2); }
.sga-bar div { height: 8px; border-radius: 99px; background: #eef1f7; overflow: hidden; }
.sga-bar div span { display: block; height: 100%; border-radius: 99px; background: var(--grad); }
.sga-bar.miss div span { background: linear-gradient(90deg, #f79009, #f04438); }
.sga-bar em { font-style: normal; color: var(--muted); text-align: right; }
.sga-chip { display: inline-block; border-radius: 8px; padding: 3px 9px; margin: 0 5px 6px 0; font-size: .78rem; font-weight: 600; }
.sga-chip.ok { background: #e7f6ee; color: #067647; }
.sga-chip.miss { background: #fef0ef; color: #b42318; }
.sga-float { position: absolute; z-index: 2; background: #fff; border: 1px solid var(--line); border-radius: 16px;
  box-shadow: 0 12px 32px rgba(16,24,40,.14); padding: 10px 14px; font-size: .8rem; color: var(--ink-2);
  display: flex; align-items: center; gap: 10px; animation: sga-float 6s ease-in-out infinite; }
.sga-float b { display: block; color: var(--ink); font-size: .9rem; }
.sga-float .ico { width: 30px; height: 30px; border-radius: 10px; display: grid; place-items: center; color: #fff; background: var(--grad); }
.sga-float .ico svg { width: 16px; height: 16px; }
.sga-float.one { top: -4px; left: -26px; }
.sga-float.two { bottom: 6px; right: -6px; animation-delay: -3s; }
.sga-float.two .ico { background: linear-gradient(135deg, #12b76a, #0e9f6e); }
@keyframes sga-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
@media (prefers-reduced-motion: reduce) { .sga-float { animation: none; } }

/* --- Stats band and sections ------------------------------------------------------------ */
.sga-stats { display: grid; grid-template-columns: repeat(4, 1fr); margin: 34px 0 8px; background: var(--surface);
  border: 1px solid var(--line); border-radius: 22px; box-shadow: var(--shadow); overflow: hidden; }
.sga-stat { padding: 20px 22px; border-left: 1px solid var(--line); }
.sga-stat:first-child { border-left: 0; }
.sga-stat b { display: block; font-size: 1.9rem; font-weight: 800; letter-spacing: -.03em; background: var(--grad);
  -webkit-background-clip: text; background-clip: text; color: transparent; line-height: 1.15; }
.sga-stat span { color: var(--muted); font-size: .88rem; }
.sga-kicker { text-align: center; text-transform: uppercase; letter-spacing: .14em; font-size: .74rem; font-weight: 700;
  color: var(--brand); margin: 70px 0 8px; }
.sga-section-title { text-align: center; font-size: 2.3rem; font-weight: 800; color: var(--ink); margin: 0 0 10px;
  letter-spacing: -0.03em; line-height: 1.15; }
.sga-section-lead { text-align: center; color: var(--muted); font-size: 1.04rem; margin: 0 auto 28px !important;
  max-width: 640px; display: block; line-height: 1.6; }
.sga-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 18px; }
.sga-card { position: relative; background: var(--surface); border: 1px solid var(--line); border-radius: 20px;
  padding: 22px 22px 24px; box-shadow: var(--shadow); transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
.sga-card:hover { transform: translateY(-3px); border-color: #d3dcf3; box-shadow: var(--shadow-lg); }
.sga-card h4 { margin: 16px 0 6px; font-size: 1.04rem; font-weight: 700; color: var(--ink); padding: 0; }
.sga-card p { margin: 0; color: var(--muted); font-size: .92rem; line-height: 1.55; }
.sga-icon { width: 44px; height: 44px; border-radius: 13px; display: grid; place-items: center; color: #fff;
  background: var(--grad); box-shadow: 0 8px 18px rgba(47,111,228,.28); }
.sga-icon svg { width: 21px; height: 21px; }
.sga-icon.c2 { background: linear-gradient(135deg, #f79009, #ef6820); box-shadow: 0 8px 18px rgba(239,104,32,.26); }
.sga-icon.c3 { background: linear-gradient(135deg, #12b76a, #079455); box-shadow: 0 8px 18px rgba(18,183,106,.26); }
.sga-icon.c4 { background: linear-gradient(135deg, #ee46bc, #9e44e6); box-shadow: 0 8px 18px rgba(158,68,230,.26); }
.sga-steps { counter-reset: step; }
.sga-step-num { position: absolute; top: 18px; right: 20px; font-size: 2.6rem; font-weight: 800; line-height: 1;
  color: transparent; -webkit-text-stroke: 1.5px #dbe3f5; letter-spacing: -.04em; }

/* --- Analyzer ------------------------------------------------------------------------------ */
.sga-card-title { display: flex; align-items: center; gap: 10px; font-size: 1.12rem; font-weight: 700; color: var(--ink);
  margin: 2px 0 10px; }
.sga-card-title .n { width: 26px; height: 26px; border-radius: 8px; display: grid; place-items: center; font-size: .82rem;
  color: #fff; background: var(--grad); }
.sga-results-head { display: flex; align-items: center; gap: 12px; margin: 34px 0 2px; }
.sga-results-head h2 { margin: 0; padding: 0; font-size: 2rem; font-weight: 800; letter-spacing: -.03em; }
.sga-results-head .pill { font-size: .78rem; font-weight: 600; color: #067647; background: #e7f6ee; border-radius: 999px; padding: 4px 10px; }
.sga-results-sub { color: var(--muted); font-size: .95rem; margin: 0; }

.sga-assure { list-style: none; padding: 0; margin: 14px 0 4px; display: grid; gap: 12px; }
.sga-assure li { display: flex; gap: 12px; align-items: flex-start; margin: 0; padding: 12px 14px; border-radius: 14px;
  background: #f7f9fd; border: 1px solid #edf0f7; }
.sga-assure svg { flex: 0 0 18px; width: 18px; height: 18px; color: var(--brand); margin-top: 2px; }
.sga-assure b { display: block; color: var(--ink); font-size: .9rem; font-weight: 600; }
.sga-assure span { color: var(--muted); font-size: .84rem; line-height: 1.45; }

/* --- Motion ------------------------------------------------------------------------- */
@keyframes sga-shine { to { background-position: 200% center; } }
@keyframes sga-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes sga-grow { from { width: 0; } }
@keyframes sga-draw { from { stroke-dasharray: 0 var(--len); } }
@keyframes sga-scroll { to { transform: translateX(-50%); } }
@keyframes sga-pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(47,111,228,.45); } 50% { box-shadow: 0 0 0 6px rgba(47,111,228,0); } }
.sga-title .hl { background: linear-gradient(90deg, #2f6fe4, #7048e8, #c246d6, #7048e8, #2f6fe4);
  background-size: 200% auto; -webkit-background-clip: text; background-clip: text; color: transparent;
  animation: sga-shine 7s linear infinite; }
.sga-eyebrow .tag { animation: sga-pulse 2.6s ease-in-out infinite; }
.sga-eyebrow, .sga-title, .sga-lead, .sga-checks { animation: sga-rise .7s cubic-bezier(.2,.7,.2,1) both; }
.sga-title { animation-delay: .05s; } .sga-lead { animation-delay: .12s; } .sga-checks { animation-delay: .2s; }
.sga-stage { animation: sga-rise .9s .15s cubic-bezier(.2,.7,.2,1) both; }
.sga-bar div span, .sga-mini-bars i, .sga-prio .meter span { animation: sga-grow 1.2s .3s cubic-bezier(.2,.7,.2,1) both; }
.sga-ring .arc { animation: sga-draw 1.4s .1s cubic-bezier(.2,.7,.2,1) both; }

/* --- Marquee -------------------------------------------------------------------------- */
.sga-marquee-label { text-align: center; color: var(--muted); font-size: .82rem; margin: 30px 0 12px; }
.sga-marquee { overflow: hidden; -webkit-mask-image: linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent);
  mask-image: linear-gradient(90deg, transparent, #000 10%, #000 90%, transparent); }
.sga-marquee .track { display: flex; gap: 10px; width: max-content; animation: sga-scroll 45s linear infinite; }
.sga-marquee span { white-space: nowrap; padding: 8px 16px; border-radius: 999px; background: rgba(255,255,255,.85);
  border: 1px solid var(--line); color: var(--ink-2); font-size: .88rem; font-weight: 500; box-shadow: var(--shadow-sm); }
.sga-marquee:hover .track { animation-play-state: paused; }

/* --- Bento ---------------------------------------------------------------------------- */
.sga-bento { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.sga-bento .span2 { grid-column: span 2; }
.sga-demo-quote { margin-top: 16px; padding: 14px 16px; border-radius: 14px; background: #f7f9fd; border: 1px solid #edf0f7;
  color: var(--ink-2); font-size: .92rem; line-height: 1.7; }
.sga-demo-quote mark { background: rgba(47,111,228,.12); color: #1d4fb8; padding: 1px 6px; border-radius: 6px; font-weight: 600; }
.sga-demo-quote mark.nice { background: rgba(112,72,232,.10); color: #5b3cc4; border: 1px dashed rgba(112,72,232,.45); }
.sga-mini-bars { display: grid; gap: 9px; margin-top: 16px; }
.sga-mini-bars div { display: grid; grid-template-columns: 60px 1fr; align-items: center; gap: 10px; font-size: .78rem; color: var(--ink-2); }
.sga-mini-bars i { display: block; height: 8px; border-radius: 99px; background: linear-gradient(90deg, #f79009, #ef6820); }
.sga-mini-bars i.h { background: repeating-linear-gradient(135deg, rgba(239,104,32,.75) 0 4px, rgba(239,104,32,.25) 4px 8px); }
.sga-langs { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.sga-langs span { font-weight: 700; font-size: .8rem; letter-spacing: .04em; color: #067647; background: #e7f6ee;
  border-radius: 10px; padding: 6px 10px; }
.sga-card.dark { background: radial-gradient(500px 220px at 90% 0%, rgba(112,72,232,.45), transparent 60%),
  radial-gradient(400px 220px at 0% 100%, rgba(47,111,228,.35), transparent 60%), #0b1430; border-color: #1b2547; }
.sga-card.dark h4 { color: #fff; } .sga-card.dark p { color: #b8c2dc; }
.sga-privacy { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.sga-privacy span { display: inline-flex; align-items: center; gap: 7px; color: #e3e8f6; font-size: .84rem;
  padding: 7px 12px; border-radius: 999px; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12); }
.sga-privacy svg { width: 15px; height: 15px; color: #6ce9a6; }
.sga-steps .sga-card:not(:last-child)::after { content: "→"; position: absolute; right: -15px; top: 50%; transform: translateY(-50%);
  width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; background: #fff; color: var(--brand);
  border: 1px solid var(--line); box-shadow: var(--shadow-sm); font-weight: 700; z-index: 2; }

/* --- Results: ring and priorities --------------------------------------------------------- */
.sga-ring { text-align: center; padding: 6px 4px 0; }
.sga-ring svg { width: 210px; height: 210px; filter: drop-shadow(0 14px 28px rgba(47,111,228,.18)); }
.sga-ring .v { font-size: 38px; font-weight: 800; fill: var(--ink); letter-spacing: -.03em; font-family: Inter, sans-serif; }
.sga-ring .l { font-size: 12px; fill: var(--muted); font-family: Inter, sans-serif; }
.sga-ring-verdict { display: inline-block; margin-top: 4px; padding: 4px 12px; border-radius: 999px; font-size: .82rem;
  font-weight: 700; color: var(--brand); background: var(--brand-soft); }
.sga-ring p { color: var(--muted); font-size: .86rem; line-height: 1.5; margin: 10px auto 0; max-width: 260px; }
.sga-prio { display: grid; gap: 10px; }
.sga-prio-item { display: grid; grid-template-columns: 36px minmax(0, 1fr) auto 122px; align-items: center; gap: 14px;
  padding: 12px 14px; border-radius: 16px; background: var(--surface); border: 1px solid var(--line); box-shadow: var(--shadow-sm);
  transition: border-color .15s, transform .15s, box-shadow .15s; }
.sga-prio-item:hover { border-color: #cdd9f4; transform: translateX(2px); box-shadow: var(--shadow); }
.sga-prio-item .rank { width: 36px; height: 36px; border-radius: 11px; display: grid; place-items: center; font-weight: 800;
  color: #fff; background: var(--grad); }
.sga-prio-item:nth-child(n+2) .rank { background: #eef2fb; color: var(--brand); }
.sga-prio-item .info b { display: block; color: var(--ink); font-size: .98rem; }
.sga-prio-item .info small { color: var(--muted); font-size: .8rem; }
.sga-prio-item .meter { height: 6px; border-radius: 99px; background: #eef1f7; margin-top: 7px; overflow: hidden; max-width: 260px; }
.sga-prio-item .meter span { display: block; height: 100%; border-radius: 99px; background: var(--grad); }
.sga-prio-item .tags { display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; }
.sga-prio-item .t { font-size: .74rem; font-weight: 600; border-radius: 999px; padding: 3px 9px; white-space: nowrap; }
.sga-prio-item .t.req { background: #fef0ef; color: #b42318; }
.sga-prio-item .t.nice { background: #f2f4f7; color: #475467; }
.sga-prio-item .t.lvl { background: #fff4e5; color: #b54708; }
.sga-prio-item .learn { text-align: center; white-space: nowrap; font-size: .84rem; font-weight: 600; color: var(--brand) !important;
  text-decoration: none !important; padding: 7px 12px; border-radius: 999px; background: var(--brand-soft); }
.sga-prio-item .learn:hover { background: var(--brand); color: #fff !important; }

/* --- Closing call to action ---------------------------------------------------------------- */
.sga-cta { position: relative; overflow: hidden; margin-top: 72px; padding: 38px 40px; border-radius: 26px; display: flex;
  align-items: center; justify-content: space-between; gap: 24px; flex-wrap: wrap; color: #fff;
  background: radial-gradient(600px 260px at 85% -20%, rgba(194,70,214,.55), transparent 60%),
    radial-gradient(520px 260px at 0% 120%, rgba(47,111,228,.6), transparent 60%), #0b1430;
  box-shadow: 0 30px 70px rgba(11,20,48,.28); }
.sga-cta h3 { color: #fff; margin: 0 0 8px; padding: 0; font-size: 1.7rem; font-weight: 800; letter-spacing: -.02em; }
.sga-cta p { color: #c3cbe2; margin: 0; max-width: 560px; }
.sga-cta-btn { display: inline-block; padding: 13px 24px; border-radius: 999px; background: #fff; color: var(--ink) !important;
  font-weight: 700; text-decoration: none !important; box-shadow: 0 10px 24px rgba(0,0,0,.25); transition: transform .15s; }
.sga-cta-btn:hover { transform: translateY(-2px); }

@media (prefers-reduced-motion: reduce) {
  .sga-title .hl, .sga-eyebrow .tag, .sga-marquee .track, .sga-eyebrow, .sga-title, .sga-lead, .sga-checks, .sga-stage,
  .sga-bar div span, .sga-mini-bars i, .sga-prio .meter span, .sga-ring .arc { animation: none; }
}
@media (max-width: 900px) {
  .sga-bento { grid-template-columns: 1fr; } .sga-bento .span2 { grid-column: auto; }
  .sga-steps .sga-card::after { display: none; }
  .sga-prio-item { grid-template-columns: 36px minmax(0, 1fr) 122px; } .sga-prio-item .tags { display: none; }
  .sga-cta { padding: 28px 24px; }
}

/* --- Footer --------------------------------------------------------------------------------- */
.sga-footer { margin-top: 64px; padding: 26px 26px 22px; background: var(--surface); border: 1px solid var(--line);
  border-radius: 22px; box-shadow: var(--shadow-sm); display: flex; flex-wrap: wrap; justify-content: space-between;
  align-items: center; gap: 14px; color: var(--muted); font-size: .88rem; }
.sga-footer .brand { display: flex; align-items: center; gap: 10px; color: var(--ink); font-weight: 700; }
.sga-footer .brand small { display: block; color: var(--muted); font-weight: 400; font-size: .82rem; }
.sga-footer a { color: var(--ink-2) !important; text-decoration: none !important; margin-left: 16px; font-weight: 500; }
.sga-footer a:hover { color: var(--brand) !important; }

@media (max-width: 900px) {
  .sga-title { font-size: 2.6rem; }
  .sga-stats { grid-template-columns: repeat(2, 1fr); }
  .sga-stat:nth-child(3) { border-left: 0; }
  .sga-stat:nth-child(n+3) { border-top: 1px solid var(--line); }
  .sga-links .by { display: none; }
  .sga-stage { padding: 26px 0 34px; }
}
@media (max-width: 640px) {
  .sga-title { font-size: 2.35rem; }
  .sga-nav { padding: 8px 8px 8px 10px; }
  .sga-version { display: none; }
  .sga-links .lbl { display: none; }
  .sga-links a { padding: 7px 9px; }
  .sga-float.one { left: 0; top: -2px; }
  .sga-float.two { right: 0; }
  .sga-section-title { font-size: 1.8rem; }
  .sga-stat b { font-size: 1.6rem; }
}
</style>
"""

_LOGO_SVG = (
    '<svg width="32" height="32" viewBox="0 0 64 64" aria-hidden="true"><defs><linearGradient id="lg" x1="0" y1="0" '
    'x2="1" y2="1"><stop offset="0" stop-color="#2f6fe4"/><stop offset="1" stop-color="#7048e8"/></linearGradient></defs>'
    '<rect width="64" height="64" rx="16" fill="url(#lg)"/><rect x="13" y="34" width="9" height="17" rx="3" fill="#fff"/>'
    '<rect x="27.5" y="24" width="9" height="27" rx="3" fill="#fff"/><rect x="42" y="13" width="9" height="38" rx="3" '
    'fill="#fff" fill-opacity="0.45"/><path d="M42 13h9v12h-9z" fill="#fff"/></svg>'
)


def _icon(paths: str) -> str:
    """A stroke icon in the style of Lucide (24x24 grid, currentColor)."""
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
    )


_ICONS = {
    "search": _icon('<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>'),
    "chart": _icon('<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>'),
    "globe": _icon('<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>'),
    "lock": _icon('<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'),
    "file": _icon('<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
                  '<path d="M16 13H8"/><path d="M16 17H8"/>'),
    "briefcase": _icon('<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/>'),
    "target": _icon('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>'),
    "check": _icon('<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>'),
    "book": _icon('<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'),
    "github": _icon('<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5'
                    '-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.4 5.4 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85'
                    ' 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/>'),
    "linkedin": _icon('<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z"/><rect width="4" height="12" x="2"'
                      ' y="9"/><circle cx="4" cy="4" r="2"/>'),
    "doc": _icon('<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><path d="M12 18v-6"/>'
                 '<path d="m9 15 3 3 3-3"/>'),
}

# A static example card shown in the hero, so visitors see the result at a glance.
_PREVIEW = f"""
<div class="sga-stage">
  <div class="sga-float one"><span class="ico">{_ICONS["book"]}</span><span>Top study priority<b>Tableau · 5 of 12 posts</b></span></div>
  <div class="sga-preview">
    <div class="sga-preview-head"><span class="sga-dots"><i></i><i></i><i></i></span><span>Example · 12 job posts · Data Analyst</span></div>
    <div class="sga-preview-row">
      <svg width="118" height="118" viewBox="0 0 120 120" aria-label="72% coverage">
        <defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#2f6fe4"/><stop offset="1" stop-color="#7048e8"/></linearGradient></defs>
        <circle cx="60" cy="60" r="48" fill="none" stroke="#eef1f7" stroke-width="13"/>
        <circle cx="60" cy="60" r="48" fill="none" stroke="url(#g)" stroke-width="13" stroke-linecap="round"
          stroke-dasharray="217 302" transform="rotate(-90 60 60)"/>
        <text x="60" y="64" text-anchor="middle" font-size="25" font-weight="800" fill="#0b1430" font-family="Inter, sans-serif">72%</text>
        <text x="60" y="81" text-anchor="middle" font-size="9.5" fill="#667085" font-family="Inter, sans-serif">coverage</text>
      </svg>
      <div class="sga-preview-kpi"><span><b>18 / 25</b> skills in your CV</span><span><b>3</b> study priorities</span>
        <span><b>PDF</b> report ready</span></div>
    </div>
    <div class="sga-bars">
      <div class="sga-bar"><span>SQL</span><div><span style="width:92%"></span></div><em>11</em></div>
      <div class="sga-bar"><span>Power BI</span><div><span style="width:67%"></span></div><em>8</em></div>
      <div class="sga-bar miss"><span>Tableau</span><div><span style="width:42%"></span></div><em>5</em></div>
    </div>
    <div><span class="sga-chip ok">✓ Python · 7</span><span class="sga-chip ok">✓ Excel · 6</span>
      <span class="sga-chip miss">✕ dbt · 3</span></div>
  </div>
  <div class="sga-float two"><span class="ico">{_ICONS["check"]}</span><span>Report<b>skill_gap_report.pdf</b></span></div>
</div>
"""

_STEPS = [
    ("file", "Upload your CV", "A text-based PDF, or paste its text."),
    ("briefcase", "Paste job posts", "One or more posts, separated by a line with ---."),
    ("target", "Get your gap", "Coverage, study priorities with free resources, the evidence and a PDF report."),
]


def render_header() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="sga-nav">
  <div class="sga-brand">{_LOGO_SVG}<span>Skill Gap Analyzer</span><span class="sga-version">v{__version__}</span></div>
  <div class="sga-links"><span class="by">Built by <b>{AUTHOR}</b></span>
  <a href="{AUTHOR_URL}" target="_blank" aria-label="GitHub">{_ICONS["github"]}<span class="lbl">GitHub</span></a>
  <a href="{LINKEDIN_URL}" target="_blank" aria-label="LinkedIn">{_ICONS["linkedin"]}<span class="lbl">LinkedIn</span></a></div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_hero(dictionary: SkillDictionary, role: str, sample_folder: str) -> None:
    text_col, preview_col = st.columns([1.1, 1], gap="large", vertical_alignment="center")
    with text_col:
        st.markdown(
            """
<div class="sga-eyebrow"><span class="tag">New</span>Works for any job title, in 6 languages</div>
<h1 class="sga-title">Find your <span class="hl">skill gap</span><br>in 30 seconds</h1>
<p class="sga-lead">Compare your CV with real job posts:
see which skills employers ask for, which ones you are missing and what to study first.</p>
""",
            unsafe_allow_html=True,
        )
        buttons = st.columns([1.25, 1, 0.35], vertical_alignment="center")
        buttons[0].button(
            "Try with sample data", icon=":material/play_arrow:", on_click=load_sample_data,
            args=(sample_folder,), type="primary", width="stretch",
            help="Fictional job posts and CV for the selected target role "
            "(or for Data Analyst, when the role has no sample).",
        )
        buttons[1].markdown('<a class="sga-ghost" href="#how-it-works">How it works →</a>',
                            unsafe_allow_html=True)
        st.markdown(
            '<p class="sga-checks">' + "".join(
                f'<span>{_ICONS["check"]}{item}</span>'
                for item in ("No sign-up", "Nothing stored", "PDF report", "Free")
            ) + "</p>",
            unsafe_allow_html=True,
        )
    with preview_col:
        st.markdown(_PREVIEW, unsafe_allow_html=True)

    stats = [
        (known_skills_label(), "skills and synonyms recognised"),
        ("6", "European languages, also mixed"),
        (str(len(get_dictionary_files())), "ready-made roles, plus any job title"),
        ("0", "bytes of your CV stored"),
    ]
    st.markdown(
        '<div class="sga-stats">'
        + "".join(f'<div class="sga-stat"><b>{value}</b><span>{label}</span></div>' for value, label in stats)
        + "</div>",
        unsafe_allow_html=True,
    )
    roles = ["Data Analyst", "Software Developer", "Digital Marketing", "Accountant", "HR Specialist",
             "Project Manager", "Sales Manager", "Data Engineer", "Nurse", "Chef", "Architect", "Teacher",
             "Customer Success", "Financial Controller", "Recruiter", "Web Developer", "Logistics", "Pharmacist"]
    chips = "".join(f"<span>{role}</span>" for role in roles)
    st.markdown(
        '<div class="sga-marquee-label">Works for every job title, from data to the kitchen</div>'
        f'<div class="sga-marquee"><div class="track">{chips}{chips}</div></div>',
        unsafe_allow_html=True,
    )


def _section(kicker: str, title: str, lead: str, anchor: str = "") -> str:
    anchor_attr = f' id="{anchor}"' if anchor else ""
    return (
        f'<div class="sga-kicker"{anchor_attr}>{kicker}</div><div class="sga-section-title">{title}</div>'
        f'<p class="sga-section-lead">{lead}</p>'
    )


def render_features() -> None:
    langs = "".join(f"<span>{code}</span>" for code in ("EN", "IT", "FR", "DE", "ES", "PT"))
    bento = f"""
<div class="sga-bento">
  <div class="sga-card span2">
    <div class="sga-icon">{_ICONS["search"]}</div><h4>Explainable, no AI</h4>
    <p>Skills are recognised with a list of {known_skills_label()} skills and their synonyms, and the app shows
    the exact sentence that matched.</p>
    <div class="sga-demo-quote">“We are looking for an analyst with strong <mark>SQL</mark> and <mark>Power BI</mark>,
    good <mark>Excel</mark> and a working knowledge of <mark class="nice">Python</mark> (nice to have).”</div>
  </div>
  <div class="sga-card">
    <div class="sga-icon c2">{_ICONS["chart"]}</div><h4>Weighted by demand</h4>
    <p>Skills most employers require count more; nice-to-have skills count half.</p>
    <div class="sga-mini-bars"><div><span>SQL</span><i style="width:92%"></i></div>
      <div><span>Tableau</span><i style="width:60%"></i></div>
      <div><span>Python</span><i class="h" style="width:38%"></i></div></div>
  </div>
  <div class="sga-card">
    <div class="sga-icon c3">{_ICONS["globe"]}</div><h4>6 European languages</h4>
    <p>Job posts in {LANGUAGES}, also mixed together.</p>
    <div class="sga-langs">{langs}</div>
  </div>
  <div class="sga-card span2 dark">
    <div class="sga-icon c4">{_ICONS["lock"]}</div><h4>Private by design</h4>
    <p>Your CV is processed in memory for this session only. No account, no tracking, no copy kept anywhere.</p>
    <div class="sga-privacy"><span>{_ICONS["check"]}In memory only</span><span>{_ICONS["check"]}No sign-up</span>
      <span>{_ICONS["check"]}Gone when you close the page</span><span>{_ICONS["check"]}PDF report built on the fly</span></div>
  </div>
</div>
"""
    steps = "".join(
        f'<div class="sga-card"><span class="sga-step-num">0{number}</span><div class="sga-icon">{_ICONS[icon]}</div>'
        f"<h4>{title}</h4><p>{text}</p></div>"
        for number, (icon, title, text) in enumerate(_STEPS, start=1)
    )
    st.markdown(
        _section("Why Skill Gap Analyzer", "Read the job market like a recruiter",
                 "A transparent way to read the job market, for any role: ready-made skill lists for the "
                 "most common jobs, automatic detection for all the others.")
        + bento
        + _section("How it works", "Three steps, about a minute",
                   "No account, no upload to third parties: everything happens in this session.", "how-it-works")
        + f'<div class="sga-grid sga-steps">{steps}</div>'
        + _section("Good to know", "Honest about its limits",
                   "What the app can and cannot do, so you know how far to trust the result.", "limitations"),
        unsafe_allow_html=True,
    )
    render_limitations()
    st.markdown(
        _section("Analyze", "Analyze your CV",
                 "Choose the role, add your CV and the job posts, then click Analyze.", "analyze"),
        unsafe_allow_html=True,
    )


def render_cta() -> None:
    """A closing call to action before the footer."""
    st.markdown(
        """
<div class="sga-cta">
  <div><h3>Your next interview starts with the right skills.</h3>
  <p>Paste a few job posts, add your CV and get a study plan in under a minute. Free, private, no sign-up.</p></div>
  <a class="sga-cta-btn" href="#analyze">Analyze my CV →</a>
</div>
""",
        unsafe_allow_html=True,
    )


def render_limitations() -> None:
    """What the app cannot do: being upfront about it makes the result easier to trust."""
    with st.expander(":material/info: Limitations: what the app can and cannot do"):
        st.markdown(
            f"""
- **It only knows the skills in its lists** ({known_skills_label()} skills, with synonyms in {LANGUAGES}),
  plus, for a role you type yourself, the terms that recur in your job posts. A skill written in an
  unusual way (an uncommon abbreviation, a typo, a brand-new tool) can be missed.
- **It reads words, not meaning.** "We don't use Excel" still counts as Excel, and the app cannot
  judge how good you are at a skill: it only checks whether your CV mentions it.
- **Levels** ("advanced", "3+ years") are recognised only when written right next to the skill.
- **Scanned PDFs** are images without text: paste the text of your CV instead. Very creative
  layouts can mix up lines, but skills are still found.
- **The result is as good as the posts you paste:** 5 to 10 real posts for the same role give a
  reliable picture; a single post gives a narrow one.
- **Soft skills** are listed apart and not scored: they are shown with examples, not studied.

Missing a skill, or found a wrong match? [Tell me on LinkedIn]({LINKEDIN_URL}) and I will add it.
"""
        )


def render_footer() -> None:
    st.markdown(
        f"""
<div class="sga-footer">
  <div class="brand">{_LOGO_SVG}<span>Skill Gap Analyzer<small>v{__version__} · No AI, nothing stored · © 2026 {AUTHOR}. All rights reserved.</small></span></div>
  <div><a href="#how-it-works">How it works</a><a href="#limitations">Limitations</a>
  <a href="{AUTHOR_URL}" target="_blank">GitHub</a><a href="{LINKEDIN_URL}" target="_blank">LinkedIn</a></div>
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
            f"v{__version__} · © 2026 {AUTHOR}. All rights reserved."
        )


def render_cv_input() -> str:
    """Return the CV text, from the uploaded PDF or from the text box."""
    st.markdown('<div class="sga-card-title"><span class="n">1</span>Your CV</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Upload your CV (PDF)",
        type=["pdf"],
        key=f"cv_upload_{st.session_state.get('uploader_key', 0)}",
        help="Text-based PDFs only: scanned images cannot be read.",
    )
    with st.expander("No PDF at hand? Paste your CV text instead", expanded=False):
        st.text_area("CV text", key="cv_text_manual", height=200, label_visibility="collapsed")
    st.markdown(
        '<ul class="sga-assure">'
        + "".join(f"<li>{_ICONS[icon]}<span><b>{title}</b>{text}</span></li>" for icon, title, text in (
            ("lock", "Read in memory only", "The PDF is never saved, logged or sent to third parties."),
            ("file", "Text-based PDF, up to 5 MB", "Exported from Word, Google Docs or Canva works best."),
            ("check", "Gone when you close the page", "Nothing is kept between sessions."),
        ))
        + "</ul>",
        unsafe_allow_html=True,
    )

    if uploaded is not None:
        try:
            text = extract_text_from_pdf(uploaded.getvalue())
        except PdfReadError as exc:
            st.error(f":material/error: {exc}")
            return ""
        if not text:
            st.error(
                ":material/image_not_supported: **This PDF looks like an image (a scan), so it "
                "has no text to read.** Paste the text of your CV in the box above "
                "(\"No PDF at hand? Paste your CV text instead\"), or export it again as a text PDF."
            )
        else:
            st.caption(f":material/check_circle: Read {len(text.split()):,} words from **{uploaded.name}**.")
        return text
    return st.session_state.cv_text_manual


def render_custom_skills(posts: list[str], dictionary: SkillDictionary, role: str) -> SkillDictionary:
    """For a typed role: let the user review the skills detected in the posts."""
    suggestions = suggest_terms(posts, dictionary, role)
    with st.container(border=True):
        st.markdown(f"#### :material/auto_awesome: Skills detected for *{role}*")
        st.caption(
            "There is no ready-made skill list for this role, so the app also looks for the terms "
            "that keep coming back in your job posts (on top of hundreds of known skills). "
            "Remove the wrong ones and type any skill that is missing, then click Analyze."
        )
        terms = st.multiselect(
            "Skills from the job posts", suggestions, default=suggestions,
            key=f"custom_terms_{hash(tuple(suggestions))}", accept_new_options=True,
            placeholder="Type a skill and press Enter", label_visibility="collapsed",
        )
    return add_custom_skills(dictionary, terms)


def render_posts_input() -> list[str]:
    """Return the list of job posts, from either input mode."""
    st.markdown('<div class="sga-card-title"><span class="n">2</span>Job posts</div>', unsafe_allow_html=True)
    st.caption(f":material/translate: Posts can be in {LANGUAGES}, and you can mix languages freely.")
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


def priority_badge(row) -> str:
    """Required skills and nice-to-have-only skills look different."""
    return ":red-badge[required]" if row.required_count else ":gray-badge[nice to have]"


def render_missing_skills(missing) -> None:
    """Missing skills by demand (#1 = top study priority), each with a free resource."""
    if missing.empty:
        st.markdown("_Nothing missing!_")
        return
    resources = get_resources()
    lines = []
    for rank, row in enumerate(missing.itertuples(), start=1):
        title, url = resources_for(row.skill, resources)[0]
        lines.append(
            f"`#{rank}` **{row.skill}** · {row.posts_count} post{'s' * (row.posts_count != 1)} "
            f"{priority_badge(row)} · [{'Learn it' if 'Search' not in title else 'Find a course'} ↗]({url})"
        )
    box = st.container(height=420, border=False) if len(lines) > 12 else st.container(border=False)
    box.markdown("  \n".join(lines))


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
        f"the result, and to spot wrong matches to [report on LinkedIn]({LINKEDIN_URL})."
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
            phrases = get_cv_phrases()
            with st.expander(":material/edit_note: Example sentences to add to your CV"):
                st.caption("Adapt them to your experience: replace the [bracketed] parts with real facts.")
                for skill in missing["skill"]:
                    for phrase in phrases.get(skill, []):
                        st.markdown(f"- **{skill}:** {phrase}")
        if not present.empty:
            st.caption("Already visible in your CV: " + ", ".join(present["skill"]))


def render_coverage_ring(score: float, n_covered: int, n_total: int) -> None:
    """The coverage score as an animated gradient ring."""
    circumference = 2 * 3.14159 * 74
    filled = circumference * max(0.0, min(score, 100.0)) / 100
    verdict = ("Strong match" if score >= 75 else "Good base" if score >= 50
               else "Room to grow" if score >= 25 else "Early stage")
    st.markdown(
        f"""
<div class="sga-ring">
  <svg viewBox="0 0 180 180" aria-label="{score:.0f}% weighted coverage">
    <defs><linearGradient id="rg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2f6fe4"/>
      <stop offset="1" stop-color="#7048e8"/></linearGradient></defs>
    <circle cx="90" cy="90" r="74" fill="none" stroke="#e3e9f5" stroke-width="16"/>
    <circle class="arc" cx="90" cy="90" r="74" fill="none" stroke="url(#rg)" stroke-width="16" stroke-linecap="round"
      stroke-dasharray="{filled:.1f} {circumference:.1f}" style="--len:{circumference:.1f}" transform="rotate(-90 90 90)"/>
    <text x="90" y="92" text-anchor="middle" class="v">{score:.0f}%</text>
    <text x="90" y="116" text-anchor="middle" class="l">weighted coverage</text>
  </svg>
  <div class="sga-ring-verdict">{verdict}</div>
  <p>{n_covered} of {n_total} requested technical skills are in your CV, weighted by how often employers ask for them.</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_priorities(technical) -> None:
    st.markdown(f"#### :material/school: Top {TOP_PRIORITIES} study priorities")
    priorities = study_priorities(technical, TOP_PRIORITIES)
    if priorities.empty:
        st.success("Your CV covers every requested technical skill. Well done!")
        return
    resources = get_resources()
    items = []
    for rank, row in enumerate(priorities.itertuples(), start=1):
        title, url = resources_for(row.skill, resources)[0]
        share = row.posts_share * 100
        tags = [f'<span class="t req">Required in {row.required_count}</span>' if row.required_count else ""]
        if row.nice_count:
            tags.append(f'<span class="t nice">Nice in {row.nice_count}</span>')
        if getattr(row, "level_count", 0):
            tags.append(f'<span class="t lvl">Level asked in {row.level_count}</span>')
        items.append(
            f'<div class="sga-prio-item"><span class="rank">{rank}</span>'
            f'<div class="info"><b>{html.escape(row.skill)}</b><small>{html.escape(row.category)} · '
            f'in {share:.0f}% of the posts</small><div class="meter"><span style="width:{max(share, 4):.0f}%"></span></div></div>'
            f'<div class="tags">{"".join(tags)}</div>'
            f'<a class="learn" href="{html.escape(url)}" target="_blank" rel="noopener" title="{html.escape(title)}">'
            f'{"Learn it" if not title.startswith("Search") else "Find a course"} ↗</a></div>'
        )
    st.markdown(f'<div class="sga-prio">{"".join(items)}</div>', unsafe_allow_html=True)


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
        cv_phrases=get_cv_phrases(),
    )

    # --- Header row and headline numbers ------------------------------------
    title_col, download_col = st.columns([3, 1], vertical_alignment="bottom")
    title_col.markdown(
        f'<div class="sga-results-head"><h2>Your results</h2><span class="pill">Analysis ready</span></div>'
        f'<p class="sga-results-sub">{n_posts} job post{"s" * (n_posts != 1)} · {dictionary.domain}</p>',
        unsafe_allow_html=True,
    )
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
    kpi[1].metric("Job posts", n_posts, border=True)
    kpi[2].metric("Skills you have", f"{n_covered} of {len(technical)}", border=True,
                  help="Requested technical skills found in your CV.")
    kpi[3].metric("Skills to learn", len(technical) - n_covered, border=True,
                  help="Requested technical skills missing from your CV.")

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
            render_coverage_ring(score, n_covered, len(technical))
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
        st.caption(
            "Technical skills, most requested first: #1 is your top study priority. The number is how "
            "many job posts ask for the skill; grey skills appear only as nice to have."
        )
        present = technical[technical["in_cv"]]
        missing = technical[~technical["in_cv"]]
        col_present, col_missing = st.columns(2)
        with col_present.container(border=True):
            st.markdown(f"**:material/check_circle: In your CV ({len(present)})**")
            st.markdown(
                " ".join(
                    f":{'green' if row.required_count else 'gray'}-badge[:material/check: {row.skill} · {row.posts_count}]"
                    for row in present.itertuples()
                ) if not present.empty else "_None yet._"
            )
        with col_missing.container(border=True):
            st.markdown(f"**:material/cancel: Missing from your CV ({len(missing)})**")
            render_missing_skills(missing)
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
        custom_role = role not in dictionary_files
        dictionary = get_all_skills() if custom_role else get_dictionary(dictionary_files[role])
    except DictionaryError as exc:
        st.error(f"The skill dictionary could not be loaded: {exc}")
        st.stop()
    if custom_role:
        dictionary = replace(dictionary, domain=role, description=role)
    sample_folder = "" if custom_role else Path(dictionary_files[role]).stem

    render_sidebar(dictionary)
    render_header()
    render_hero(dictionary, role, sample_folder)
    render_features()

    # --- The analyser ---------------------------------------------------------
    with st.container(border=True):
        col_role, col_weight, col_clear = st.columns([2, 2, 1], vertical_alignment="bottom")
        col_role.selectbox(
            ":material/work: Target role", list(dictionary_files), key="role",
            accept_new_options=True,
            help="Pick a ready-made role or type any job title (e.g. Nurse, Chef, Architect): "
            "for a typed role the skills are detected in the job posts themselves.",
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

    if custom_role and posts:
        dictionary = render_custom_skills(posts, dictionary, role)

    missing_inputs = [label for label, given in (("your CV", cv_text.strip()), ("at least one job post", posts))
                      if not given]
    st.button(
        "Analyze my skill gap", icon=":material/insights:", type="primary",
        width="stretch", on_click=start_analysis, disabled=bool(missing_inputs), key="analyze",
    )
    if missing_inputs:
        st.caption(":material/info: To analyze, add " + " and ".join(missing_inputs) + ".")

    if st.session_state.analyzed and posts:
        st.markdown('<div id="your-results"></div>', unsafe_allow_html=True)
        if not cv_text.strip():
            st.info(
                "No CV yet: upload it (or paste its text) to compare it with the market. "
                "Meanwhile, here is what the job posts ask for.",
                icon=":material/info:",
            )
        with st.spinner("Analyzing your CV and the job posts…", show_time=True):
            render_results(cv_text, posts, dictionary, nice_weight)
        scroll_to_results()
    else:
        st.caption(
            ":material/lock: Your CV and the job posts stay in memory for this session only "
            "and are discarded when you close the page."
        )
    render_cta()
    render_footer()


main()
