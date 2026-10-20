"""Build the downloadable PDF report of the results.

The PDF is drawn with fpdf2 (pure Python, no system dependency, works on
Streamlit Community Cloud). It is generated in memory and returned as bytes:
nothing is written to disk.

Privacy: the report lists skill names, counts and scores only. It never
contains the text of the CV or of the job posts.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from fpdf import FPDF
from fpdf.fonts import FontFace

# Colours (RGB) from the app's palette.
_BLUE = (42, 120, 214)
_BLUE_LIGHT = (205, 226, 251)
_INK = (31, 31, 30)
_MUTED = (82, 81, 78)
_RULE = (227, 226, 222)
_GREEN = (0, 99, 0)
_GREEN_BG = (230, 244, 230)
_RED = (163, 33, 33)
_RED_BG = (251, 233, 233)
_ORANGE = (138, 74, 0)
_ORANGE_BG = (253, 240, 225)

_MAX_BARS = 12
_HEADING = FontFace(emphasis="BOLD", color=_MUTED)


def _latin1(text: str) -> str:
    """The core PDF fonts cover Latin-1: replace anything outside it."""
    text = text.replace("–", "-").replace("—", "-").replace("…", "...")
    return text.encode("latin-1", "replace").decode("latin-1")


class _Report(FPDF):
    def __init__(self, footer_text: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.footer_text = footer_text
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=20)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*_MUTED)
        self.cell(0, 5, _latin1(self.footer_text), align="L")
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="R")

    # --- small building blocks ------------------------------------------------
    def section(self, title: str, subtitle: str = "") -> None:
        if self.get_y() > 245:
            self.add_page()
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*_INK)
        self.cell(0, 8, _latin1(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*_RULE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        if subtitle:
            self.set_font("Helvetica", size=9)
            self.set_text_color(*_MUTED)
            self.multi_cell(0, 4.5, _latin1(subtitle), new_x="LMARGIN", new_y="NEXT")
            self.ln(1)

    def chips(self, names: list[str], fg, bg) -> None:
        """Skill names as small rounded labels that wrap across lines."""
        if not names:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(*_MUTED)
            self.cell(0, 6, "None.", new_x="LMARGIN", new_y="NEXT")
            return
        self.set_font("Helvetica", size=8.5)
        x0, right, h, gap = self.l_margin, self.w - self.r_margin, 6, 1.6
        x, y = x0, self.get_y()
        for name in names:
            label = _latin1(name)
            w = self.get_string_width(label) + 5
            if x + w > right:
                x, y = x0, y + h + gap
            self.set_fill_color(*bg)
            self.set_text_color(*fg)
            self.rect(x, y, w, h, style="F", round_corners=True, corner_radius=1.5)
            self.set_xy(x, y)
            self.cell(w, h, label, align="C")
            x += w + gap
        self.set_xy(x0, y + h + 3)

    def bars(self, rows: list[tuple[str, float, str, tuple]], max_value: float) -> None:
        """Horizontal bars: (label, value, text at the end, colour)."""
        label_w, bar_x = 52, self.l_margin + 54
        bar_w_max = self.w - self.r_margin - bar_x - 22
        for label, value, end_text, colour in rows:
            if self.get_y() > 270:
                self.add_page()
            y = self.get_y()
            self.set_font("Helvetica", size=8.5)
            self.set_text_color(*_INK)
            self.set_xy(self.l_margin, y)
            self.cell(label_w, 5.5, _latin1(label), align="R")
            width = bar_w_max * (value / max_value) if max_value else 0
            self.set_fill_color(*colour)
            if width > 0:
                self.rect(bar_x, y + 1, max(width, 0.8), 3.6, style="F", round_corners=True, corner_radius=1)
            self.set_xy(bar_x + width + 1.5, y)
            self.set_text_color(*_MUTED)
            self.cell(20, 5.5, _latin1(end_text))
            self.set_xy(self.l_margin, y + 6)


def build_pdf_report(
    table: pd.DataFrame,
    soft: pd.DataFrame,
    breakdown: pd.DataFrame,
    priorities: pd.DataFrame,
    extras: list[str],
    *,
    role: str,
    n_posts: int,
    coverage: float,
    nice_weight: float,
    version: str,
    generated_on: date | None = None,
    resources: dict[str, list[tuple[str, str]]] | None = None,
) -> bytes:
    """Return the PDF report as bytes.

    Args:
        table: the technical skills of the skill table (see `analysis.split_soft_skills`).
        soft: the soft skills of the skill table, reported in their own section.
        breakdown: the output of `analysis.category_breakdown`.
        priorities: the output of `analysis.study_priorities`.
        extras: skills in the CV that no post asked for.
        role: the target role (dictionary name) shown in the header.
        n_posts: number of job posts analysed.
        coverage: weighted coverage score, 0-100.
        nice_weight: weight used for nice-to-have skills.
        version: app version, printed in the footer.
        generated_on: report date (defaults to today).
        resources: free learning resources per skill (see `resources.py`).
    """
    from skill_gap.resources import resources_for
    generated_on = generated_on or date.today()
    present = table[table["in_cv"]]
    missing = table[~table["in_cv"]]

    pdf = _Report(footer_text=f"Skill Gap Analyzer v{version} - skill-gap.streamlit.app")
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- Header band ------------------------------------------------------------
    pdf.set_fill_color(*_BLUE)
    pdf.rect(0, 0, pdf.w, 38, style="F")
    pdf.set_xy(18, 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 10, "Skill Gap Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(
        0, 6,
        _latin1(f"Target role: {role}  |  {n_posts} job posts analysed  |  {generated_on.isoformat()}"),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_y(46)

    # --- KPI cards ----------------------------------------------------------------
    cards = [
        (f"{coverage:.0f}%", "Weighted coverage", "technical skills"),
        (f"{len(present)} of {len(table)}", "Technical skills", "in your CV"),
        (str(len(missing)), "Missing", "technical skills"),
    ]
    card_w, gap, y = (pdf.w - 36 - 2 * 6) / 3, 6, pdf.get_y()
    for i, (value, label, sub) in enumerate(cards):
        x = 18 + i * (card_w + gap)
        pdf.set_draw_color(*_RULE)
        pdf.set_fill_color(248, 248, 247)
        pdf.rect(x, y, card_w, 24, style="DF", round_corners=True, corner_radius=2.5)
        pdf.set_xy(x + 4, y + 3)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*(_BLUE if i == 0 else _INK))
        pdf.cell(card_w - 8, 9, _latin1(value))
        pdf.set_xy(x + 4, y + 13)
        pdf.set_font("Helvetica", size=8.5)
        pdf.set_text_color(*_MUTED)
        pdf.cell(card_w - 8, 4.5, _latin1(label))
        pdf.set_xy(x + 4, y + 17.5)
        pdf.cell(card_w - 8, 4.5, _latin1(sub))
    # Coverage progress bar under the cards.
    pdf.set_y(y + 28)
    bar_w = pdf.w - 36
    pdf.set_fill_color(*_BLUE_LIGHT)
    pdf.rect(18, pdf.get_y(), bar_w, 2.5, style="F", round_corners=True, corner_radius=1)
    pdf.set_fill_color(*_BLUE)
    pdf.rect(18, pdf.get_y(), max(bar_w * coverage / 100, 1), 2.5, style="F", round_corners=True, corner_radius=1)
    pdf.ln(5)

    # --- Study priorities ------------------------------------------------------------
    pdf.section(f"Top {len(priorities)} study priorities" if not priorities.empty else "Study priorities",
                "Missing technical skills, most requested first.")
    if priorities.empty:
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(*_GREEN)
        pdf.cell(0, 7, "Your CV covers every requested technical skill.", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(*_INK)
        pdf.set_draw_color(*_RULE)
        pdf.set_fill_color(255, 255, 255)
        with pdf.table(
            col_widths=(8, 52, 48, 22, 22, 22),
            text_align=("RIGHT", "LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT"),
            headings_style=_HEADING,
            line_height=6,
            borders_layout="HORIZONTAL_LINES",
            cell_fill_mode="NONE",
        ) as t:
            header = t.row()
            for h in ("#", "Skill", "Category", "Required", "Nice", "Share"):
                header.cell(h)
            for i, row in enumerate(priorities.itertuples(), start=1):
                r = t.row()
                for value in (str(i), row.skill, row.category, str(row.required_count),
                              str(row.nice_count), f"{row.posts_share * 100:.0f}%"):
                    r.cell(_latin1(value))

        # Where to learn each priority, as clickable links.
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_INK)
        pdf.cell(0, 5, "Where to start learning (free):", new_x="LMARGIN", new_y="NEXT")
        for row in priorities.itertuples():
            title, url = resources_for(row.skill, resources or {})[0]
            pdf.set_font("Helvetica", size=8.5)
            pdf.set_text_color(*_INK)
            pdf.cell(42, 5, _latin1(row.skill))
            pdf.set_text_color(*_BLUE)
            pdf.cell(0, 5, _latin1(title), link=url, new_x="LMARGIN", new_y="NEXT")

    # --- Most requested skills ---------------------------------------------------------
    top = table.head(_MAX_BARS)
    pdf.section(
        "Most requested technical skills",
        "Number of job posts asking for each skill. Dark bar = in your CV, light bar = missing.",
    )
    pdf.bars(
        [(r.skill, r.posts_count, str(r.posts_count), _BLUE if r.in_cv else _BLUE_LIGHT)
         for r in top.itertuples()],
        max_value=max(1, int(top["posts_count"].max())) if not top.empty else 1,
    )

    # --- Coverage by category --------------------------------------------------------------
    pdf.section("Coverage by category", "Weighted coverage of the technical skills in each category.")
    pdf.bars(
        [(r.category, r.coverage_pct, f"{r.coverage_pct:.0f}%  ({r.covered}/{r.requested})", _BLUE)
         for r in breakdown.itertuples()],
        max_value=100,
    )

    # --- CV vs market ------------------------------------------------------------------------
    pdf.section("Your CV vs the market", "Technical skills requested by the posts.")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_GREEN)
    pdf.cell(0, 6, f"In your CV ({len(present)})", new_x="LMARGIN", new_y="NEXT")
    pdf.chips([f"{r.skill} - {r.posts_count}" for r in present.itertuples()], _GREEN, _GREEN_BG)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*_RED)
    pdf.cell(0, 6, f"Missing from your CV ({len(missing)})", new_x="LMARGIN", new_y="NEXT")
    pdf.chips([f"{r.skill} - {r.posts_count}" for r in missing.itertuples()], _RED, _RED_BG)
    if extras:
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(*_MUTED)
        pdf.multi_cell(0, 4.5, _latin1("Also in your CV but not requested: " + ", ".join(extras) + "."),
                       new_x="LMARGIN", new_y="NEXT")

    # --- Soft skills ----------------------------------------------------------------------------
    if not soft.empty:
        soft_missing = soft[~soft["in_cv"]]
        soft_present = soft[soft["in_cv"]]
        pdf.section(
            "Soft skills to make visible in your CV",
            "Not counted in the coverage score. Show them with a concrete example in your CV "
            "rather than studying them.",
        )
        pdf.chips([f"{r.skill} - {r.posts_count}" for r in soft_missing.itertuples()], _ORANGE, _ORANGE_BG)
        if not soft_present.empty:
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(*_MUTED)
            pdf.multi_cell(0, 4.5, _latin1("Already visible in your CV: " + ", ".join(soft_present["skill"]) + "."),
                           new_x="LMARGIN", new_y="NEXT")

    # --- Full table ---------------------------------------------------------------------------------
    pdf.section("All requested technical skills")
    pdf.set_font("Helvetica", size=8.5)
    pdf.set_text_color(*_INK)
    pdf.set_fill_color(255, 255, 255)
    with pdf.table(
        col_widths=(50, 46, 20, 22, 18, 18),
        text_align=("LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT", "CENTER"),
        headings_style=_HEADING,
        line_height=5.5,
        borders_layout="HORIZONTAL_LINES",
            cell_fill_mode="NONE",
    ) as t:
        header = t.row()
        for h in ("Skill", "Category", "Required", "Nice to have", "Demand", "In CV"):
            header.cell(h)
        for r in table.itertuples():
            row = t.row()
            for value in (r.skill, r.category, str(r.required_count), str(r.nice_count),
                          f"{r.demand:g}", "Yes" if r.in_cv else "No"):
                row.cell(_latin1(value))

    # --- Method note -------------------------------------------------------------------------------------
    pdf.ln(4)
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(*_MUTED)
    pdf.multi_cell(
        0, 4,
        _latin1(
            f"How to read it: demand = posts that require the skill + {nice_weight:g} x posts where it is "
            "only nice to have. Weighted coverage = demand of the technical skills in your CV / total "
            "demand. Skills are recognised with a dictionary (no AI), so wording outside the dictionary "
            "can be missed. This report contains skill names and scores only, never the text of your CV "
            "or of the job posts."
        ),
        new_x="LMARGIN", new_y="NEXT",
    )
    return bytes(pdf.output())
