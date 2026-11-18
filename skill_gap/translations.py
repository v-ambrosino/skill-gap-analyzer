"""Translations of the interface: English sentence -> translated sentence.

The keys are the exact English sentences used in the code (see `i18n.t`).
`{placeholders}` and Markdown / HTML markup must be kept as they are.
`tests/test_i18n.py` fails when a sentence of the app is missing here.
"""

ITALIAN = {
    # --- Languages, roles ---------------------------------------------------------
    "English, Italian, French, German, Spanish and Portuguese":
        "inglese, italiano, francese, tedesco, spagnolo e portoghese",
    "Accountant": "Contabile",
    "Nurse": "Infermiere",
    "Architect": "Architetto",
    "Teacher": "Insegnante",
    "Logistics": "Logistica",
    "Pharmacist": "Farmacista",
    " and ": " e ",
    "Yes": "Sì",
    "No": "No",

    # --- Navigation, hero ------------------------------------------------------------
    "Built by": "Creato da",
    "New": "Novità",
    "Works for any job title, in 6 languages": "Funziona per qualsiasi ruolo, in 6 lingue",
    'Find your <span class="hl">skill gap</span><br>in 30 seconds':
        'Scopri il tuo <span class="hl">skill gap</span><br>in 30 secondi',
    "Compare your CV with real job posts: see which skills employers ask for, which ones you are missing and what to study first.":
        "Confronta il tuo CV con annunci di lavoro reali: scopri quali competenze chiedono le aziende, "
        "quali ti mancano e cosa studiare per primo.",
    "Analyze my CV": "Analizza il mio CV",
    "Try with sample data": "Prova con dati di esempio",
    "Fictional job posts and CV for the selected target role (or for Data Analyst, when you typed your own role).":
        "Annunci e CV di fantasia per il ruolo selezionato (o per Data Analyst, se hai scritto tu il ruolo).",
    "How it works": "Come funziona",
    "No sign-up": "Senza registrazione",
    "Nothing stored": "Nessun dato salvato",
    "PDF report": "Report PDF",
    "Free": "Gratis",
    "Top study priority": "Prima priorità di studio",
    "Tableau · 5 of 12 posts": "Tableau · 5 annunci su 12",
    "Example · 12 job posts · Data Analyst": "Esempio · 12 annunci · Data Analyst",
    "coverage": "copertura",
    "skills in your CV": "competenze nel tuo CV",
    "study priorities": "priorità di studio",
    "report ready": "report pronto",
    "Report": "Report",
    "skills and synonyms recognised": "competenze e sinonimi riconosciuti",
    "European languages, also mixed": "lingue europee, anche mescolate",
    "ready-made roles, plus any job title": "ruoli pronti, più qualsiasi altro ruolo",
    "bytes of your CV stored": "byte del tuo CV salvati",
    "Works for every job title, from data to the kitchen": "Funziona per ogni ruolo, dai dati alla cucina",

    # --- Features, steps, limitations ----------------------------------------------------
    "Why Skill Gap Analyzer": "Perché Skill Gap Analyzer",
    "Read the job market like a recruiter": "Leggi il mercato del lavoro come un recruiter",
    "A transparent way to read the job market, for any role: ready-made skill lists for the most common jobs, automatic detection for all the others.":
        "Un modo trasparente di leggere il mercato del lavoro, per qualsiasi ruolo: elenchi di competenze "
        "pronti per i lavori più comuni, rilevamento automatico per tutti gli altri.",
    "Explainable, no AI": "Spiegabile, senza IA",
    "Skills are recognised with a list of {count} skills and their synonyms, and the app shows the exact sentence that matched.":
        "Le competenze sono riconosciute con un elenco di {count} competenze e relativi sinonimi, e l'app "
        "mostra la frase esatta in cui le ha trovate.",
    '“We are looking for an analyst with strong <mark>SQL</mark> and <mark>Power BI</mark>, good <mark>Excel</mark> and a working knowledge of <mark class="nice">Python</mark> (nice to have).”':
        '“Cerchiamo un analista con ottima conoscenza di <mark>SQL</mark> e <mark>Power BI</mark>, buon '
        '<mark>Excel</mark> e una conoscenza di base di <mark class="nice">Python</mark> (gradita).”',
    "Weighted by demand": "Pesato sulla domanda",
    "Skills most employers require count more; nice-to-have skills count half.":
        "Le competenze richieste da più aziende contano di più; quelle solo gradite contano la metà.",
    "6 European languages": "6 lingue europee",
    "Job posts in {languages}, also mixed together.": "Annunci in {languages}, anche mescolati tra loro.",
    "Private by design": "Privato per progetto",
    "Your CV is processed in memory for this session only. No account, no tracking, no copy kept anywhere.":
        "Il tuo CV è elaborato in memoria solo per questa sessione. Nessun account, nessun tracciamento, "
        "nessuna copia conservata.",
    "Everything runs inside your browser: your CV never leaves this device. No account, no tracking, no copy kept anywhere.":
        "Tutto gira dentro il tuo browser: il tuo CV non lascia mai questo dispositivo. Nessun account, "
        "nessun tracciamento, nessuna copia conservata.",
    "Stays on this device": "Resta su questo dispositivo",
    "In memory only": "Solo in memoria",
    "Gone when you close the page": "Sparisce quando chiudi la pagina",
    "PDF report built on the fly": "Report PDF generato al momento",
    "Three steps, about a minute": "Tre passaggi, circa un minuto",
    "No account, no upload to third parties: everything happens on this device.":
        "Nessun account, nessun invio a terzi: tutto avviene su questo dispositivo.",
    "No account, no upload to third parties: everything happens in this session.":
        "Nessun account, nessun invio a terzi: tutto avviene in questa sessione.",
    "Upload your CV": "Carica il tuo CV",
    "A text-based PDF, or paste its text.": "Un PDF con testo selezionabile, oppure incolla il testo.",
    "Paste job posts": "Incolla gli annunci",
    "One or more posts, separated by a line with ---.": "Uno o più annunci, separati da una riga con ---.",
    "Get your gap": "Scopri il tuo gap",
    "Coverage, study priorities with free resources, the evidence and a PDF report.":
        "Copertura, priorità di studio con risorse gratuite, le frasi trovate e un report PDF.",
    "Good to know": "Da sapere",
    "Honest about its limits": "Onesto sui propri limiti",
    "What the app can and cannot do, so you know how far to trust the result.":
        "Cosa l'app sa e non sa fare, così sai quanto fidarti del risultato.",
    "Limitations: what the app can and cannot do": "Limiti: cosa l'app sa e non sa fare",
    "Limitations": "Limiti",
    '\n- **It only knows the skills in its lists** ({count} skills, with synonyms in {languages}),\n  plus, for a role you type yourself, the terms that recur in your job posts. A skill written in an\n  unusual way (an uncommon abbreviation, a typo, a brand-new tool) can be missed.\n- **It reads words, not meaning.** "We don\'t use Excel" still counts as Excel, and the app cannot\n  judge how good you are at a skill: it only checks whether your CV mentions it.\n- **Levels** ("advanced", "3+ years") are recognised only when written right next to the skill.\n- **Scanned PDFs** are images without text: paste the text of your CV instead. Very creative\n  layouts can mix up lines, but skills are still found.\n- **The result is as good as the posts you paste:** 5 to 10 real posts for the same role give a\n  reliable picture; a single post gives a narrow one.\n- **Soft skills** are listed apart and not scored: they are shown with examples, not studied.\n\nMissing a skill, or found a wrong match? [Tell me on LinkedIn]({url}) and I will add it.\n':
        "\n- **Conosce solo le competenze dei suoi elenchi** ({count} competenze, con sinonimi in {languages}),\n"
        "  più, per un ruolo scritto da te, i termini che ricorrono nei tuoi annunci. Una competenza scritta in\n"
        "  modo insolito (un'abbreviazione rara, un refuso, uno strumento nuovissimo) può sfuggire.\n"
        "- **Legge le parole, non il significato.** \"Non usiamo Excel\" conta comunque come Excel, e l'app non\n"
        "  può giudicare quanto sei bravo in una competenza: controlla solo se il tuo CV la nomina.\n"
        "- **I livelli** (\"avanzato\", \"3+ anni\") sono riconosciuti solo se scritti accanto alla competenza.\n"
        "- **I PDF scansionati** sono immagini senza testo: incolla invece il testo del tuo CV. Impaginazioni\n"
        "  molto creative possono mescolare le righe, ma le competenze vengono comunque trovate.\n"
        "- **Il risultato vale quanto gli annunci che incolli:** da 5 a 10 annunci reali per lo stesso ruolo\n"
        "  danno un quadro affidabile; un solo annuncio ne dà uno ristretto.\n"
        "- **Le soft skill** sono elencate a parte e non contano nel punteggio: si dimostrano con esempi, non si studiano.\n\n"
        "Manca una competenza o hai trovato un abbinamento sbagliato? [Scrivimi su LinkedIn]({url}) e la aggiungo.\n",
    "Your next interview starts with the right skills.": "Il tuo prossimo colloquio inizia dalle competenze giuste.",
    "Paste a few job posts, add your CV and get a study plan in under a minute. Free, private, no sign-up.":
        "Incolla qualche annuncio, aggiungi il tuo CV e ottieni un piano di studio in meno di un minuto. "
        "Gratis, privato, senza registrazione.",
    "No AI, nothing stored": "Niente IA, nessun dato salvato",
    "All rights reserved.": "Tutti i diritti riservati.",

    # --- Sidebar ----------------------------------------------------------------------------
    "Privacy": "Privacy",
    "**Your CV never leaves this device.** This version runs entirely inside your browser: the CV and the job posts are not uploaded to any server, nothing is saved, and everything is gone when you close the tab.":
        "**Il tuo CV non lascia mai questo dispositivo.** Questa versione gira interamente nel tuo browser: "
        "il CV e gli annunci non vengono inviati a nessun server, nulla viene salvato e tutto sparisce "
        "quando chiudi la scheda.",
    "**No data is stored.** Your CV and the job posts are processed **in memory only** for this session: nothing is saved to disk, logged, cached or sent to external services or AI. Close the tab and everything is gone.":
        "**Nessun dato viene salvato.** Il tuo CV e gli annunci sono elaborati **solo in memoria** per questa "
        "sessione: nulla viene scritto su disco, registrato nei log, messo in cache o inviato a servizi "
        "esterni o IA. Chiudi la scheda e tutto sparisce.",
    "The online version runs on Streamlit Community Cloud: files are processed in that server's memory and never stored. For full control, run the app locally (see the README).":
        "La versione online gira su Streamlit Community Cloud: i file sono elaborati nella memoria di quel "
        "server e mai salvati. Per il pieno controllo, esegui l'app in locale (vedi il README).",
    "1. Skills are recognised with an editable **dictionary** of **{count} skills**, with synonyms in {languages}.\n2. Each skill counts **once per job post**: 1 if the post **requires** it, less if it is only **nice to have** (see Advanced settings).\n3. **Coverage** = share of the requested technical skills found in your CV, weighted by that demand.":
        "1. Le competenze sono riconosciute con un **dizionario** modificabile di **{count} competenze**, "
        "con sinonimi in {languages}.\n"
        "2. Ogni competenza conta **una volta per annuncio**: 1 se l'annuncio la **richiede**, meno se è "
        "solo **gradita** (vedi Impostazioni avanzate).\n"
        "3. **Copertura** = quota delle competenze tecniche richieste presenti nel tuo CV, pesata su quella domanda.",

    # --- Analyzer inputs ----------------------------------------------------------------------
    "Analyze": "Analizza",
    "Analyze your CV": "Analizza il tuo CV",
    "Choose the role, add your CV and the job posts, then click Analyze.":
        "Scegli il ruolo, aggiungi il tuo CV e gli annunci, poi clicca Analizza.",
    "Target role": "Ruolo obiettivo",
    "Pick a ready-made role or type any job title (e.g. Nurse, Chef, Architect): for a typed role the skills are detected in the job posts themselves.":
        "Scegli un ruolo pronto o scrivi qualsiasi ruolo (es. Infermiere, Chef, Architetto): per un ruolo "
        "scritto da te le competenze vengono rilevate negli annunci stessi.",
    "Advanced settings": "Impostazioni avanzate",
    "Weight of nice-to-have skills": "Peso delle competenze gradite",
    'A post that requires a skill counts 1. A post where the skill is only nice to have ("is a plus", "gradita", "von Vorteil", "se valorará") counts this much. 0 ignores nice-to-have skills, 1 treats them as requirements.':
        'Un annuncio che richiede una competenza conta 1. Un annuncio in cui la competenza è solo gradita '
        '("is a plus", "gradita", "von Vorteil", "se valorará") conta quanto indicato qui. 0 ignora le '
        'competenze gradite, 1 le tratta come requisiti.',
    "Clear all": "Cancella tutto",
    "Your CV": "Il tuo CV",
    "Upload your CV (PDF)": "Carica il tuo CV (PDF)",
    "Text-based PDFs only: scanned images cannot be read.":
        "Solo PDF con testo: le immagini scansionate non possono essere lette.",
    "No PDF at hand? Paste your CV text instead": "Non hai il PDF? Incolla il testo del tuo CV",
    "CV text": "Testo del CV",
    "Read on this device only": "Letto solo su questo dispositivo",
    "The PDF never leaves your browser: nothing is uploaded.":
        "Il PDF non lascia mai il tuo browser: nulla viene caricato.",
    "Read in memory only": "Letto solo in memoria",
    "The PDF is never saved, logged or sent to third parties.":
        "Il PDF non viene mai salvato, registrato nei log o inviato a terzi.",
    "Text-based PDF, up to 5 MB": "PDF con testo, fino a 5 MB",
    "Exported from Word, Google Docs or Canva works best.":
        "Esportato da Word, Google Docs o Canva funziona meglio.",
    "Nothing is kept between sessions.": "Nulla viene conservato tra una sessione e l'altra.",
    '**This PDF looks like an image (a scan), so it has no text to read.** Paste the text of your CV in the box above ("No PDF at hand? Paste your CV text instead"), or export it again as a text PDF.':
        '**Questo PDF sembra un\'immagine (una scansione), quindi non contiene testo da leggere.** Incolla il '
        'testo del tuo CV nel riquadro qui sopra ("Non hai il PDF? Incolla il testo del tuo CV"), oppure '
        'esportalo di nuovo come PDF con testo.',
    "Read {words} words from **{name}**.": "Lette {words} parole da **{name}**.",
    "Job posts": "Annunci",
    "Posts can be in {languages}, and you can mix languages freely.":
        "Gli annunci possono essere in {languages}, anche in lingue diverse tra loro.",
    "Input mode": "Modalità di inserimento",
    "One text box (separate posts with ---)": "Un solo riquadro (separa gli annunci con ---)",
    "One field per job post": "Un campo per annuncio",
    "Paste one or more job posts": "Incolla uno o più annunci",
    "First job post...\n---\nSecond job post...\n---\nThird job post...":
        "Primo annuncio...\n---\nSecondo annuncio...\n---\nTerzo annuncio...",
    "Put a line with three dashes (---) between two job posts. Languages: {languages}.":
        "Metti una riga con tre trattini (---) tra un annuncio e l'altro. Lingue: {languages}.",
    "Job post #{n}": "Annuncio n. {n}",
    "Remove": "Rimuovi",
    "Add job post": "Aggiungi annuncio",
    "Skills detected for *{role}*": "Competenze rilevate per *{role}*",
    "There is no ready-made skill list for this role, so the app also looks for the terms that keep coming back in your job posts (on top of hundreds of known skills). Remove the wrong ones and type any skill that is missing, then click Analyze.":
        "Per questo ruolo non c'è un elenco di competenze pronto, quindi l'app cerca anche i termini che "
        "ricorrono nei tuoi annunci (oltre a centinaia di competenze note). Rimuovi quelli sbagliati e "
        "scrivi le competenze mancanti, poi clicca Analizza.",
    "Skills from the job posts": "Competenze dagli annunci",
    "Type a skill and press Enter": "Scrivi una competenza e premi Invio",
    "Analyze my skill gap": "Analizza il mio skill gap",
    "To analyze, add {what}.": "Per analizzare, aggiungi {what}.",
    "your CV": "il tuo CV",
    "at least one job post": "almeno un annuncio",
    "No CV yet: upload it (or paste its text) to compare it with the market. Meanwhile, here is what the job posts ask for.":
        "Manca ancora il CV: caricalo (o incolla il testo) per confrontarlo con il mercato. Intanto, ecco "
        "cosa chiedono gli annunci.",
    "Analyzing your CV and the job posts…": "Analisi del CV e degli annunci in corso…",
    "Your CV and the job posts stay on this device and are discarded when you close the page.":
        "Il tuo CV e gli annunci restano su questo dispositivo e vengono eliminati quando chiudi la pagina.",
    "Your CV and the job posts stay in memory for this session only and are discarded when you close the page.":
        "Il tuo CV e gli annunci restano in memoria solo per questa sessione e vengono eliminati quando "
        "chiudi la pagina.",
    "The skill dictionary could not be loaded: {error}": "Impossibile caricare il dizionario delle competenze: {error}",

    # --- Results ------------------------------------------------------------------------------
    "No known skills were found in the job posts. Check that you pasted the full text, pick another target role above, or extend the dictionaries in data/dictionaries/.":
        "Negli annunci non è stata trovata nessuna competenza nota. Controlla di aver incollato il testo "
        "completo, scegli un altro ruolo qui sopra oppure estendi i dizionari in data/dictionaries/.",
    "No technical skills to score: the posts list only soft skills, or only nice-to-have skills with a weight of 0 (see Advanced settings).":
        "Nessuna competenza tecnica da valutare: gli annunci elencano solo soft skill, oppure solo "
        "competenze gradite con peso 0 (vedi Impostazioni avanzate).",
    "Your results": "I tuoi risultati",
    "Analysis ready": "Analisi pronta",
    "{n} job post": "{n} annuncio",
    "{n} job posts": "{n} annunci",
    "{n} post": "{n} annuncio",
    "{n} posts": "{n} annunci",
    "Download PDF report": "Scarica il report PDF",
    "Weighted coverage": "Copertura pesata",
    "weighted coverage": "copertura pesata",
    "Requested technical skills found in your CV, weighted by how many posts ask for each one (nice-to-have skills count less, see Advanced settings). Soft skills are listed separately and not scored.":
        "Competenze tecniche richieste presenti nel tuo CV, pesate su quanti annunci chiedono ciascuna "
        "(quelle gradite contano meno, vedi Impostazioni avanzate). Le soft skill sono elencate a parte "
        "e non contano nel punteggio.",
    "Skills you have": "Competenze che hai",
    "{covered} of {total}": "{covered} su {total}",
    "Requested technical skills found in your CV.": "Competenze tecniche richieste presenti nel tuo CV.",
    "Skills to learn": "Competenze da imparare",
    "Requested technical skills missing from your CV.": "Competenze tecniche richieste assenti dal tuo CV.",
    "Overview": "Panoramica",
    "Skills": "Competenze",
    "Evidence": "Frasi trovate",
    "Strong match": "Ottima corrispondenza",
    "Good base": "Buona base",
    "Room to grow": "Margine di crescita",
    "Early stage": "Fase iniziale",
    "{covered} of {total} requested technical skills are in your CV, weighted by how often employers ask for them.":
        "{covered} delle {total} competenze tecniche richieste sono nel tuo CV, pesate su quanto spesso "
        "le aziende le chiedono.",
    "Top {n} study priorities": "Le {n} priorità di studio",
    "Study priorities": "Priorità di studio",
    "Your CV covers every requested technical skill. Well done!":
        "Il tuo CV copre tutte le competenze tecniche richieste. Ottimo lavoro!",
    "Your CV covers every requested technical skill.": "Il tuo CV copre tutte le competenze tecniche richieste.",
    "Based on only {n} job post:": "Basato su {n} solo annuncio:",
    "Based on only {n} job posts:": "Basato su soli {n} annunci:",
    "many skills are asked equally often, so among those the skills most typical of the role come first. Add at least {min} posts for a reliable ranking.":
        "molte competenze sono richieste con la stessa frequenza, quindi tra quelle vengono prima le più "
        "tipiche del ruolo. Aggiungi almeno {min} annunci per una classifica affidabile.",
    "{n} missing skills are asked equally often as the last ones listed here: among those, the skills most typical of the role come first.":
        "{n} competenze mancanti sono richieste con la stessa frequenza delle ultime elencate qui: tra "
        "quelle, vengono prima le più tipiche del ruolo.",
    "Required in {n}": "Richiesta in {n}",
    "Nice in {n}": "Gradita in {n}",
    "Level asked in {n}": "Livello chiesto in {n}",
    "in {share}% of the posts": "nel {share}% degli annunci",
    "Learn it": "Impara",
    "Find a course": "Cerca un corso",
    "Soft skills to make visible in your CV": "Soft skill da rendere visibili nel tuo CV",
    "Every soft skill the posts ask for is already visible in your CV.":
        "Tutte le soft skill richieste dagli annunci sono già visibili nel tuo CV.",
    'Employers ask for these soft skills, but your CV does not mention them in words the app recognises. They are not counted in the coverage score: rather than studying them, show them with a concrete example, e.g. "presented monthly results to the sales team" for communication.':
        'Le aziende chiedono queste soft skill, ma il tuo CV non le nomina con parole che l\'app riconosce. '
        'Non contano nel punteggio di copertura: invece di studiarle, dimostrale con un esempio concreto, '
        'ad es. "ho presentato i risultati mensili al team vendite" per la comunicazione.',
    "Example sentences to add to your CV": "Frasi di esempio da aggiungere al tuo CV",
    "Adapt them to your experience: replace the [bracketed] parts with real facts. The examples are in English.":
        "Adattale alla tua esperienza: sostituisci le parti [tra parentesi] con fatti reali. Gli esempi sono in inglese.",
    "Already visible in your CV: ": "Già visibili nel tuo CV: ",
    "Which job posts fit you best": "A quali annunci sei più adatto",
    "The same weighted coverage, computed for each job post on its own: the best match comes first. Red skills are required by that post, grey ones are only nice to have. Soft skills are not counted.":
        "La stessa copertura pesata, calcolata per ogni singolo annuncio: il più adatto viene per primo. "
        "Le competenze in rosso sono richieste da quell'annuncio, quelle in grigio sono solo gradite. "
        "Le soft skill non contano.",
    "Add more job posts to compare them and see where you fit best.":
        "Aggiungi altri annunci per confrontarli e vedere a quale sei più adatto.",
    "Missing": "Mancanti",
    "Nice": "Gradite",
    "You have": "Hai",
    "No technical skills found in this post": "Nessuna competenza tecnica trovata in questo annuncio",
    "You have all {total} requested technical skills": "Hai tutte le {total} competenze tecniche richieste",
    "You have {covered} of {total} requested technical skills":
        "Hai {covered} delle {total} competenze tecniche richieste",
    "Most requested skills": "Competenze più richieste",
    "Skills to show": "Competenze da mostrare",
    "Group by category": "Raggruppa per categoria",
    "Your CV vs the market": "Il tuo CV e il mercato",
    "Technical skills, most requested first: #1 is your top study priority. The number is how many job posts ask for the skill; grey skills appear only as nice to have.":
        "Competenze tecniche, dalla più richiesta: la n. 1 è la tua prima priorità di studio. Il numero "
        "indica quanti annunci chiedono la competenza; quelle in grigio compaiono solo come gradite.",
    "In your CV ({n})": "Nel tuo CV ({n})",
    "Missing from your CV ({n})": "Assenti dal tuo CV ({n})",
    "None yet.": "Ancora nessuna.",
    "Nothing missing!": "Non manca nulla!",
    "required": "richiesta",
    "nice to have": "gradita",
    "Also in your CV but not requested by these posts: ": "Presenti nel tuo CV ma non richieste da questi annunci: ",
    "Coverage by category": "Copertura per categoria",
    "Full skill table": "Tabella completa delle competenze",
    "Skill": "Competenza",
    "Category": "Categoria",
    "Posts": "Annunci",
    "Required": "Richiesta",
    "Nice to have": "Gradita",
    "Demand": "Domanda",
    "Share of posts (%)": "Quota di annunci (%)",
    "In CV": "Nel CV",
    "Level asked": "Livello chiesto",
    "Where each skill was found": "Dove è stata trovata ogni competenza",
    "Pick a skill to see the exact sentences that matched. Useful to check the result, and to spot wrong matches to [report on LinkedIn]({url}).":
        "Scegli una competenza per vedere le frasi esatte in cui è stata trovata. Utile per verificare il "
        "risultato e per individuare abbinamenti sbagliati da [segnalare su LinkedIn]({url}).",
    "In the job posts": "Negli annunci",
    "In your CV": "Nel tuo CV",
    "phrase split across lines": "frase spezzata su più righe",
    "Not found in your CV.": "Non trovata nel tuo CV.",
    "Found (phrase split across lines).": "Trovata (frase spezzata su più righe).",
    "Your PDF report": "Il tuo report PDF",
    "A ready-to-share summary: coverage, the top study priorities, the match with each job post, the most requested skills, coverage by category, your CV vs the market, the soft skills to show and the full skill table.":
        "Un riepilogo pronto da condividere: copertura, priorità di studio, corrispondenza con ogni "
        "annuncio, competenze più richieste, copertura per categoria, il tuo CV e il mercato, le soft "
        "skill da mostrare e la tabella completa delle competenze.",
    "Generated in memory for this session only. It contains skill names and scores, never the text of your CV or of the job posts.":
        "Generato in memoria solo per questa sessione. Contiene nomi di competenze e punteggi, mai il "
        "testo del tuo CV o degli annunci.",

    # --- Charts -----------------------------------------------------------------------------------
    "Required in {required} of {total} posts": "Richiesta in {required} annunci su {total}",
    "Nice to have in {nice}": "Gradita in {nice}",
    "In your CV: {answer}": "Nel tuo CV: {answer}",
    "Hatched = nice to have": "Tratteggio = gradita",
    "Number of job posts": "Numero di annunci",

    # --- PDF report ---------------------------------------------------------------------------------
    "Skill Gap Report": "Report Skill Gap",
    "{n} job post analysed": "{n} annuncio analizzato",
    "{n} job posts analysed": "{n} annunci analizzati",
    "technical skills": "competenze tecniche",
    "Technical skills": "Competenze tecniche",
    "in your CV": "nel tuo CV",
    "Missing technical skills, most requested first.": "Competenze tecniche mancanti, dalla più richiesta.",
    "Share": "Quota",
    "Where to start learning (free):": "Da dove iniziare a studiare (gratis):",
    "Weighted coverage of each job post on its own, best match first, with the required technical skills you are missing for it.":
        "Copertura pesata di ogni singolo annuncio, dal più adatto, con le competenze tecniche richieste "
        "che ti mancano per ciascuno.",
    "Most requested technical skills": "Competenze tecniche più richieste",
    "Number of job posts asking for each skill. Dark bar = in your CV, light bar = missing.":
        "Numero di annunci che chiedono ogni competenza. Barra scura = nel tuo CV, barra chiara = mancante.",
    "Weighted coverage of the technical skills in each category.":
        "Copertura pesata delle competenze tecniche in ogni categoria.",
    "Technical skills requested by the posts.": "Competenze tecniche richieste dagli annunci.",
    "Also in your CV but not requested: ": "Presenti nel tuo CV ma non richieste: ",
    "Not counted in the coverage score. Show them with a concrete example in your CV rather than studying them.":
        "Non contano nel punteggio di copertura. Dimostrale con un esempio concreto nel tuo CV invece di studiarle.",
    "Example sentences for your CV:": "Frasi di esempio per il tuo CV:",
    "All requested technical skills": "Tutte le competenze tecniche richieste",
    "How to read it: demand = posts that require the skill + {weight} x posts where it is only nice to have. Weighted coverage = demand of the technical skills in your CV / total demand. Skills are recognised with a dictionary (no AI), so wording outside the dictionary can be missed. This report contains skill names and scores only, never the text of your CV or of the job posts.":
        "Come leggerlo: domanda = annunci che richiedono la competenza + {weight} x annunci in cui è solo "
        "gradita. Copertura pesata = domanda delle competenze tecniche nel tuo CV / domanda totale. Le "
        "competenze sono riconosciute con un dizionario (senza IA), quindi formulazioni fuori dal "
        "dizionario possono sfuggire. Questo report contiene solo nomi di competenze e punteggi, mai il "
        "testo del tuo CV o degli annunci.",
    "Page {page}/{pages}": "Pagina {page}/{pages}",
    "None.": "Nessuna.",
}

TRANSLATIONS = {"it": ITALIAN}
