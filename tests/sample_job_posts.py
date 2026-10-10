"""Fictional job posts and CVs used by the tests (English and Italian).

Companies and people are invented. Each text is short and targeted, so every
test can state exactly which skills it expects.
"""

POST_EN_DATA_ANALYST = """
Data Analyst - Acme Analytics (fictional)
We need someone fluent in SQL and Python (pandas, NumPy) to build dashboards
in Power BI. Experience with A/B testing and stakeholder management is a plus.
You will report directly to the Head of Data.
"""

POST_IT_BI_ANALYST = """
BI Analyst - Azienda Esempio S.p.A. (fittizia)
Cerchiamo una persona con ottima conoscenza di Excel e PowerBI, capacità
analitiche e attitudine al lavoro di squadra. Gradita la conoscenza di Tableau
e della visualizzazione dei dati. Ambiente dinamico e agile.
"""

POST_EN_WITH_R = """
Junior Analyst (fictional)
Must have: SQL, R or Python. Our R&D department in Rome works with SAP R/3.
Nice to have: statistics, regression and time series.
"""

CV_EN = """
Jane Q. Example
Skills: SQL, Python (pandas), Excel, data visualisation, teamwork.
Built weekly reports and dashboards for the sales team.
"""

# Three posts that share some skills, with known overlaps, for the analysis tests.
POSTS_FOR_ANALYSIS = [
    "Requirements: SQL, Excel, Power BI.",
    "Requirements: SQL, Python, Tableau.",
    "Requisiti: SQL, Excel, comunicazione.",
]
