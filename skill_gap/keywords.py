"""Suggest skills for a role without a dictionary, straight from the job posts.

No AI: a term is suggested when it appears in several posts (or, with a single
post, more than once) and is not a common word. Common words are listed below
for the six supported languages, together with the vocabulary that every job
post uses ("experience", "team", "contract"...). The user reviews the list in
the app before it is compared with the CV.
"""

from __future__ import annotations

import re
from collections import Counter

from skill_gap.normalization import normalize_text
from skill_gap.skills_dictionary import Skill, SkillDictionary, synonym_to_regex

CUSTOM_CATEGORY = "From the job posts"
MAX_SUGGESTIONS = 15

STOPWORDS = frozenset("""
a about above across after again against all also always am among an and any are as at be been before being
below between both but by can could did do does doing done down during each either else etc even ever every
for from further get gets getting give given go going good great had has have having he her here hers him his
how however i if in into is it its itself just least less like made make makes making many may me might more
most much must my near need needed needs new no nor not now of off often on once one only or other others our
out over own per please plus quite rather really same see seek seeking several shall she should since so some
such than that the their them then there these they this those though through thus to too toward under until
up upon us use used using very via was we well were what when where whether which while who whom whose why will
with within without would yes yet you your yours
able ability abilities about applicant applicants application applications apply area areas available benefit
benefits bonus business candidate candidates career careers chance client clients company companies competitive
contract contracts culture customer customers day days degree department description desirable desired develop
developing development duties eager employee employees employer employment ensure environment equivalent excellent
experience experienced experiences field flexible full fulltime future goal goals group grow growing growth help high
highly hire hiring hours hybrid ideal ideally including insurance interest interested italian job jobs join junior
key knowledge large leading level levels life location looking manage management minimum month months motivated
offer offers office opportunity opportunities paid part people person plus position positions practical preferred
previous professional profile proven provide qualification qualifications related relevant remote required
requirement requirements responsibilities responsibility responsible role roles salary senior skill skills
solid someone strong successful support team teams time tools travel understanding week weeks within work worked
working works world year years
il lo la i gli le un uno una di da del dello della dei degli delle al allo alla ai agli alle dal dallo dalla dai dagli
dalle nel nello nella nei negli nelle sul sullo sulla sui sugli sulle con per tra fra su e ed o od ma anche come che chi
cui non piu molto poco se si sono essere ha hanno abbiamo avere fare ogni nostro nostra nostri nostre vostro tuo tua
suo sua loro questo questa questi queste quello quella quelli quelle sara saranno stato essere offriamo cerchiamo
ricerchiamo ricerca cerca azienda aziende candidato candidata candidati candidature candidatura esperienza esperienze
anni anno mesi mese lavoro lavorare lavorativa lavorativo ruolo ruoli conoscenza conoscenze competenze competenza
capacita requisiti requisito richiesti richiesta richiesto preferibile preferibilmente gradita gradito graditi
titolo studio laurea diploma contratto tempo pieno indeterminato determinato sede inserimento risorsa figura
professionale buona buone buon ottima ottime ottimo forte attivita settore team gruppo clienti cliente offre
opportunita crescita ambiente dinamico giovane completano profilo descrizione mansioni principali responsabilita
supporto sviluppo gestione area ufficio orario full part time ral retribuzione benefit welfare candidarsi invia
entro oltre almeno circa minimo tutti tutte nuovi nuove nuovo nuova parte modo base livello
le la les un une des de du et ou mais pour par avec sans sur dans au aux ce cette ces nous vous ils elles est sont
etre avoir votre notre nos vos son sa ses leur leurs qui que dont plus tres experience poste profil entreprise
equipe travail connaissance connaissances competences missions mission recherchons candidat contrat annees ans
der die das ein eine einer eines einem einen und oder aber fur mit ohne auf in im am an zu zum zur von vom bei aus
nach uber unter ist sind sein haben wir sie ihr ihre unser unsere dein du ich es als auch sehr gute guten erfahrung
kenntnisse aufgaben profil stelle unternehmen team arbeit jahre bewerbung bieten suchen mitarbeiter mitarbeiterin
el los las un una unos unas y o pero para por con sin sobre en del al es son ser estar tener nuestro nuestra
nuestros su sus que como mas muy experiencia conocimiento conocimientos puesto empresa equipo trabajo buscamos
ofrecemos requisitos anos funciones perfil
o os as um uma uns umas e ou mas para por com sem sobre em no na nos nas do da dos das ao aos e sao ser estar ter
nosso nossa seu sua que como mais muito experiencia conhecimento conhecimentos vaga empresa equipe equipa trabalho
procuramos oferecemos requisitos anos funcoes perfil
""".split())

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#]*(?:[./-][A-Za-z0-9+#]+)*")
# Chunks a term can't cross: punctuation, list bullets and line breaks.
_CHUNK_SPLIT = re.compile(r"[,;:()\[\]!?\n|\"'*•·]|\.(?=\s|$)|\s[-–—]\s")


def _candidates(text: str) -> dict[str, str]:
    """Lowercase key -> surface form of each 1-3 word term in `text`."""
    found: dict[str, str] = {}
    for chunk in _CHUNK_SPLIT.split(text):
        words = _WORD.findall(chunk)
        for n in (1, 2, 3):
            for i in range(len(words) - n + 1):
                gram = words[i:i + n]
                lower = [w.lower() for w in gram]
                if any(w in STOPWORDS or w.isdigit() for w in lower):
                    continue
                if n == 1 and len(gram[0]) < 3 and not gram[0].isupper():
                    continue
                found.setdefault(" ".join(lower), " ".join(gram))
    return found


def suggest_terms(posts: list[str], dictionary: SkillDictionary, role: str = "",
                  max_terms: int = MAX_SUGGESTIONS) -> list[str]:
    """Terms that keep coming back in the posts and are not in `dictionary`."""
    role_words = {w.lower() for w in _WORD.findall(normalize_text(role))}
    doc_freq: Counter[str] = Counter()
    surface: dict[str, str] = {}
    for post in posts:
        text = normalize_text(post)
        # Skills the dictionary already knows are blanked out, so they are not suggested twice.
        for skill in dictionary.skills:
            for pattern in skill.patterns:
                text = pattern.sub(" | ", text)
        terms = _candidates(text)
        for key, form in terms.items():
            surface.setdefault(key, form)
        doc_freq.update(terms.keys())
    min_df = 2 if len(posts) >= 2 else 1
    keys = [k for k, df in doc_freq.items() if df >= min_df and not set(k.split()) <= role_words]
    # A longer term that is as frequent as its parts replaces them ("google ads" over "ads").
    keys = [k for k in keys
            if not any(other != k and f" {k} " in f" {other} " and doc_freq[other] >= doc_freq[k]
                       for other in keys)]
    keys.sort(key=lambda k: (-doc_freq[k], -len(k.split()), k))
    return [surface[k][:1].upper() + surface[k][1:] for k in keys[:max_terms]]


def merge_dictionaries(dictionaries: list[SkillDictionary], domain: str) -> SkillDictionary:
    """One dictionary with every skill of `dictionaries` (first one wins on a name clash)."""
    skills: dict[str, Skill] = {}
    categories: dict[str, None] = {}
    for dictionary in dictionaries:
        categories.update(dict.fromkeys(dictionary.categories))
        for skill in dictionary.skills:
            skills.setdefault(skill.name, skill)
    return SkillDictionary(domain, tuple(categories), tuple(skills.values()))


def add_custom_skills(dictionary: SkillDictionary, terms: list[str]) -> SkillDictionary:
    """`dictionary` plus one skill per user-approved term."""
    known = {skill.name.lower() for skill in dictionary.skills}
    extra = []
    for term in dict.fromkeys(t.strip() for t in terms):
        if term and term.lower() not in known and _WORD.search(term):
            extra.append(Skill(term, CUSTOM_CATEGORY, (synonym_to_regex(term),)))
    if not extra:
        return dictionary
    return SkillDictionary(dictionary.domain, (*dictionary.categories, CUSTOM_CATEGORY),
                           (*dictionary.skills, *extra), dictionary.description)
