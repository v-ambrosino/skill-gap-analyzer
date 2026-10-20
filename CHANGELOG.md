# Changelog

All notable changes to Skill Gap Analyzer. Versions follow
[semantic versioning](https://semver.org/); pre-release tags mark the stage.

## 1.7.2 — 2026-10-20

### Fixed
- More **ways of working and people skills move to soft skills**, so they are shown with
  examples in the CV instead of being listed as things to study: Scrum, Kanban, Waterfall,
  Documentation, Business Acumen, Requirements Gathering, Data Storytelling, Negotiation,
  Customer Service, Closing, Cold Calling, Sales Presentations, Employee Relations,
  Diversity & Inclusion and the driving licence. Each one has example CV sentences.

## 1.7.1 — 2026-10-20

### Fixed
- **Agile is now a soft skill** in every role dictionary: it is listed under "Soft skills
  to make visible in your CV" (with example CV sentences) instead of the study priorities.

## 1.7.0 — 2026-10-20

### Changed
- **Motion:** the hero fades in, the headline has a moving gradient, the preview bars and
  the coverage ring draw themselves; everything stops with "reduce motion".
- **Role marquee** under the stats: a scrolling row of job titles the app works for.
- **Bento features:** a live example of matched skills, mini demand bars, language tags
  and a dark "Private by design" card.
- Steps connected by arrows; a dark closing call to action before the footer.
- **Results:** a custom gradient coverage ring with a verdict ("Room to grow", "Strong
  match"…), and study priorities as cards with rank, share bar, required / nice / level
  tags and a "Learn it" button.

## 1.6.0 — 2026-10-20

### Changed
- **Redesigned interface:** frosted navigation bar with GitHub / LinkedIn buttons, a
  bigger hero with a gradient headline, a layered product preview with floating cards,
  a stats band (skills, languages, roles, data stored), section kickers, feature cards
  with gradient icons, numbered steps, privacy notes in the CV card, numbered input
  cards, a results header, KPI cards with an accent bar and a new footer.
- Consistent design tokens (colours, radii, layered shadows), styled inputs, upload
  area, expanders and tabs; responsive layout for phones; subtle motion that respects
  "reduce motion".
- Charts use Inter and the brand blue; the legend no longer overlaps the bars.
- Study priorities table without the category column, so the "Learn it" links fit.

## 1.5.0 — 2026-10-20

### Added
- **Limitations** section ("Good to know") in the app, with a link to report a missing
  skill or a wrong match on LinkedIn (also in the Evidence tab).
- Skill counter "Knows 300+ skills" (computed from the dictionaries) in the hero and in
  the "Explainable, no AI" card, which now speaks plain language instead of "dictionary rule".
- **Missing skills as an action plan:** ranked by demand (#1 = top study priority), each
  with a required / nice-to-have badge and a free resource to learn it.
- Skills in the CV that are only nice to have are shown in grey.
- A loading indicator while the analysis runs.

### Changed
- **Analyze** is bigger and disabled until both the CV and a job post are given, with a
  message saying what is missing.
- The job posts box says that posts can be in any of the six languages, also mixed.
- A clearer error for scanned PDFs, pointing to the paste-text box.

## 1.4.1 — 2026-10-20

### Changed
- The hero text no longer changes with the selected role.
- Header: "Built by Vincenzo Ambrosino · GitHub · LinkedIn".

## 1.4.0 — 2026-10-20

### Added
- **Any target role:** type any job title in "Target role". The app uses every known
  skill plus the terms that recur in the job posts (`skill_gap/keywords.py`, no AI),
  shown in an editable list before the analysis.
- **Six new ready-made roles:** Software Developer, Digital Marketing, Sales, Finance &
  Accounting, Human Resources, Project Manager (plus `shared/office.yaml`).
- Roles without sample data load the Data Analyst sample.

## 1.3.1 — 2026-10-20

### Changed
- Header shows "Published by: Vincenzo Ambrosino · GitHub profile" instead of the
  navigation links; the "Free · open source" badge and the source code links are gone.
- **License:** MIT replaced by "All rights reserved" (free use of the hosted app only).

## 1.3.0 — 2026-10-20

### Added
- **Example CV sentences for missing soft skills** (`data/cv_phrases.yaml`), in the
  app and in the PDF report.
- **Skill levels weigh more:** "advanced Excel", "SQL (3+ years)", "ottima conoscenza
  di Excel", "Excel avancé", "fundierte SQL-Kenntnisse"… add `LEVEL_BONUS` (0.5) to the
  skill's demand. A new "Level" column in the study priorities shows how many posts ask
  for a level.
- **Browser-only version (experimental):** `web/build.py` builds a static site
  that runs the app in the browser with stlite; published on GitHub Pages by
  `.github/workflows/pages.yml`. The CV never leaves the device.
- PDF reading falls back to `pypdf` when pdfplumber is not available.

## 1.2.0 — 2026-10-20

### Changed
- **Website-style interface:** a navigation bar instead of Streamlit's toolbar, a
  two-column hero with a live-looking result preview, "Why Skill Gap Analyzer" and
  "How it works" sections, soft-shadow cards, pill buttons and tabs, a footer, a
  soft gradient background and centred content.
- Target role and the nice-to-have weight (in *Advanced settings*) are chosen on the
  page; the sidebar starts collapsed.
- The page scrolls to the results after *Analyze* or *Try with sample data*.

## 1.1.0 — 2026-10-20

### Added
- **Six languages:** job posts in French, German, Spanish and Portuguese, besides
  English and Italian. Synonyms for every concept skill and soft skill, plus the
  words for "nice to have" (*serait un plus*, *von Vorteil*, *se valorará*,
  *diferencial*), section headers (*Profil recherché*, *Deine Aufgaben*,
  *Requisitos*, *Atividades*) and degrees (*Bac+5*, *Studium*, *Grado en*, *Formação em*).
- **PDF report** (fpdf2): header, KPI cards, coverage bar, study priorities, bar
  charts of the most requested skills and of coverage by category, CV vs market,
  soft skills and the full table. It replaces the HTML and CSV downloads.
- **New interface:** landing page with a hero and the three steps, an *Analyze*
  button, results in tabs (Overview, Skills, Evidence, Report), KPI cards, a
  coverage ring, logo, Inter font and a refined theme.

### Fixed
- French "tableau de bord" (dashboard) and "tableau croisé dynamique" (pivot table)
  no longer count as the Tableau tool.

## 1.0.0 — 2026-10-20

First stable release, live at [skill-gap.streamlit.app](https://skill-gap.streamlit.app/).

### Added
- Hosted on Streamlit Community Cloud; live demo link and badge in the README.

### Changed
- `pytest` moved to `requirements-dev.txt`: the hosted app installs only what it runs.
- Privacy wording (README and sidebar) now describes the hosted version: files are
  processed in the Streamlit server's memory and never stored.

### Fixed
- Statistics was still counted as a requested skill when a post named it as a field
  of study in other words. Now recognised as education: "neolaureato/a in",
  "lauree in", "titolo di studio", "discipline quantitative", "graduated in",
  "studies in", "education:", "quantitative background", and a list of subjects on
  the lines under "Formazione" or "Laurea in una delle seguenti discipline:".
  "Strong knowledge of statistics" still counts as the skill.

## 0.2.0-beta — 2026-10-20

First version tested on real job posts (12 Italian and English posts) and a real CV.

### Added
- **Required vs nice to have.** Section headers ("Nice to have:", "Requisiti:",
  "Costituiscono titolo preferenziale") and marker words ("is a plus", "gradita")
  decide whether a post requires a skill. A nice-to-have mention weighs 0.5
  (adjustable in the sidebar, from 0 to 1).
- **Evidence:** "Where each skill was found" quotes the sentence that matched in
  each post and in the CV.
- **Soft skills to make visible in your CV:** soft skills are listed apart and kept
  out of the coverage score, the missing skills and the study priorities.
- **Multiple roles:** one dictionary per role in `data/dictionaries/`, a Target role
  selector, shared soft skills through `include`, and a new Data Engineer /
  Analytics Engineer dictionary (87 skills).
- **Sample data per role** for "Load sample data".
- **Downloadable HTML report** (prints to PDF), next to the CSV export.
- **CI:** the test suite runs on GitHub Actions (Python 3.10 and 3.12).

### Changed
- Coverage score and priorities use demand = required + 0.5 × nice to have, on
  technical skills only.
- Emoji and symbol bullets (✅, •) in copy-pasted posts are read as line breaks.
- Post titles skip generic job-board headings ("About the job",
  "Informazioni sull'offerta di lavoro").
- Data Analyst dictionary: 119 skills, with new wording from a pre-test on
  realistic posts.

### Fixed
- "Laurea in … Statistica o affini" no longer counts as a request for Statistics
  (`degree_subject` flag); a degree in the CV still counts.
- "Nice to have: X, Y" on one line no longer turns the following lines into
  nice-to-have.
- False positives: "contratto di collaborazione", "sem." (semestre), "GTM strategy",
  "su larga scala" (Scala), JavaScript (Java).

## 0.1.0-alpha — 2026-10-10

First version, merged on 2026-10-10 (labelled 1.0.0 in the code at first, relabelled
0.1.0-alpha on 2026-10-11): CV upload (PDF), job posts in Italian or English (one text
box with `---` or one field per post), a skill dictionary of 118 skills, demand
chart by category, CV vs market comparison, weighted coverage score, top-5 study
priorities, privacy by design (nothing stored), tests and README.
