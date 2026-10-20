"""Skill Gap Analyzer: compare a CV against job posts using a skill dictionary.

Modules:
    pdf_reader         Extract text from an uploaded PDF (in memory only).
    skills_dictionary  Load and validate the YAML skill dictionary.
    extractor          Normalise text and find skills in it.
    analysis           Turn extracted skills into demand, coverage and priorities.
"""

__version__ = "1.3.1"
