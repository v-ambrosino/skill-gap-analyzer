"""Job posts in French, German, Spanish and Portuguese (all fictional)."""

import pytest

from skill_gap.extractor import NICE_TO_HAVE, REQUIRED, find_skills, find_skills_in_posts

POST_FR = """
Data Analyst (H/F) - Société Fictive (Paris)
Vos missions :
- Analyse de données et création de tableaux de bord sous Power BI
- Nettoyage des données et suivi de la qualité des données
Profil recherché :
- Diplômé(e) d'un Bac+5 en statistiques ou équivalent
- Maîtrise de SQL et d'Excel (tableaux croisés dynamiques)
- Esprit d'analyse, rigueur et travail en équipe
- Anglais courant
La connaissance de Python serait un plus.
"""

POST_DE = """
Data Analyst (m/w/d) - Fiktive GmbH (Berlin)
Deine Aufgaben:
- Datenanalyse und Datenvisualisierung mit Tableau
- Aufbau von Dashboards und Kennzahlen für das Management
Dein Profil:
- Abgeschlossenes Studium der Statistik, Informatik oder vergleichbar
- Sehr gute SQL-Kenntnisse und Erfahrung mit Python
- Analytisches Denken, Teamfähigkeit und Kommunikationsstärke
- Sehr gute Englischkenntnisse
Kenntnisse in dbt sind von Vorteil.
"""

POST_ES = """
Analista de Datos - Empresa Ficticia (Madrid)
Funciones:
- Análisis de datos y elaboración de informes en Power BI
- Limpieza de datos y modelado de datos
Requisitos:
- Grado en Estadística, Matemáticas o similar
- Dominio de SQL y Excel
- Trabajo en equipo y resolución de problemas
- Nivel alto de inglés
Se valorará experiencia con Tableau.
"""

POST_PT = """
Analista de Dados - Empresa Fictícia (Lisboa)
Atividades:
- Análise de dados e criação de dashboards em Power BI
- Garantir a qualidade dos dados
Requisitos:
- Formação em Estatística, Economia ou áreas afins
- Conhecimentos de SQL e Python
- Pensamento analítico e trabalho em equipa
Diferencial: experiência com Looker.
"""


def mentions(post, dictionary):
    [found] = find_skills_in_posts([post], dictionary)
    return {skill: m.priority for skill, m in found.items()}


@pytest.mark.parametrize(
    "post, expected, nice",
    [
        (POST_FR,
         {"Data Analysis", "Dashboarding", "Power BI", "Data Cleaning", "Data Quality",
          "SQL", "Excel", "Pivot Tables", "Analytical Thinking", "Attention to Detail",
          "Teamwork", "English", "Python"},
         {"Python"}),
        (POST_DE,
         {"Data Analysis", "Data Visualization", "Tableau", "Dashboarding", "KPI Definition",
          "SQL", "Python", "Analytical Thinking", "Teamwork", "Communication", "English", "dbt"},
         {"dbt"}),
        (POST_ES,
         {"Data Analysis", "Reporting", "Power BI", "Data Cleaning", "Data Modeling",
          "SQL", "Excel", "Teamwork", "Problem Solving", "English", "Tableau"},
         {"Tableau"}),
        (POST_PT,
         {"Data Analysis", "Dashboarding", "Power BI", "Data Quality", "SQL", "Python",
          "Analytical Thinking", "Teamwork", "Looker"},
         {"Looker"}),
    ],
    ids=["french", "german", "spanish", "portuguese"],
)
def test_european_posts(dictionary, post, expected, nice):
    found = mentions(post, dictionary)
    assert expected <= set(found)
    for skill in expected:
        assert found[skill] == (NICE_TO_HAVE if skill in nice else REQUIRED), skill
    # The degree in statistics is an education requirement, not a skill.
    assert "Statistics" not in found


def test_french_tableau_words_are_not_the_tool(dictionary):
    found = find_skills("Création de tableaux de bord et d'un tableau croisé dynamique", dictionary)
    assert "Tableau" not in found
    assert {"Dashboarding", "Pivot Tables"} <= found
    assert "Tableau" in find_skills("Maîtrise de Tableau et de Power BI", dictionary)


@pytest.mark.parametrize(
    "text, skill",
    [
        ("Gute Kenntnisse in Statistik", "Statistics"),
        ("Connaissances en statistiques", "Statistics"),
        ("Conocimientos de estadística", "Statistics"),
        ("Experiência em análise estatística", "Statistics"),
    ],
)
def test_statistics_as_a_skill_in_other_languages(dictionary, text, skill):
    assert skill in mentions(text, dictionary)
