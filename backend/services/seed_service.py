import logging

from extensions import db
from models import Goal, Skill, Tool, User, make_model


logger = logging.getLogger(__name__)


def seed_domains():
    from models import Domain, WorkflowCategory

    if Domain.query.first():
        return

    domains = [
        {
            'name': 'KI & Automatisierung',
            'icon': '🤖',
            'sort_order': 1,
            'description': 'KI-Tools, Prompt-Engineering, Automatisierung, LLMs',
            'tags': 'ki,ai,chatgpt,claude,prompt,llm,automatisierung,generieren'
        },
        {
            'name': 'Schule & Lernen',
            'icon': '📚',
            'sort_order': 2,
            'description': 'Lerntools, Recherche, Dokumente, Prüfungsvorbereitung',
            'tags': 'schule,lernen,klausur,referat,facharbeit,prüfung,abitur,recherche'
        },
        {
            'name': 'Produktivität & Office',
            'icon': '📊',
            'sort_order': 3,
            'description': 'Tabellenkalkulation, Textverarbeitung, Projektmanagement',
            'tags': 'excel,tabelle,sheets,word,dokument,präsentation,planung,office,notion'
        },
        {
            'name': 'Kreatives Arbeiten',
            'icon': '🎨',
            'sort_order': 4,
            'description': 'Design, Video, Audio, Bildbearbeitung, Präsentationen',
            'tags': 'design,video,audio,bild,grafik,canva,figma,logo,poster,schnitt'
        },
        {
            'name': 'Programmierung & Tech',
            'icon': '💻',
            'sort_order': 5,
            'description': 'Code, Debugging, Versionskontrolle, Deployment, APIs',
            'tags': 'code,python,javascript,bug,debug,github,api,programmieren,git'
        },
        {
            'name': 'Kommunikation & Team',
            'icon': '💬',
            'sort_order': 6,
            'description': 'E-Mail, Meetings, Kollaboration, Dokumentation',
            'tags': 'email,meeting,team,slack,discord,kommunikation,zusammenarbeit'
        },
        {
            'name': 'Daten & Analyse',
            'icon': '📈',
            'sort_order': 7,
            'description': 'Datenanalyse, Visualisierung, Business Intelligence',
            'tags': 'daten,analyse,statistik,visualisierung,dashboard,sql,bi'
        },
        {
            'name': 'Finanzen & Business',
            'icon': '💰',
            'sort_order': 8,
            'description': 'Buchhaltung, Steuern, Business-Planung, CRM',
            'tags': 'finanzen,buchhaltung,steuer,business,crm,rechnung,budget'
        },
    ]

    for d in domains:
        db.session.add(Domain(**d))

    db.session.commit()
    logger.info(f"Seeded {len(domains)} domains")


def seed_database():
    if User.query.first():
        return

    user = make_model(User, name="Mein Profil")
    db.session.add(user)

    skills = [
        make_model(Skill, name="Python-Grundlagen", level="Fortgeschritten"),
        make_model(Skill, name="Web-Recherche", level="Experte"),
        make_model(Skill, name="Bildbearbeitung", level="Anfänger"),
        make_model(Skill, name="Textschreiben", level="Fortgeschritten"),
        make_model(Skill, name="KI-Prompt-Engineering", level="Anfänger"),
    ]
    for skill in skills:
        db.session.add(skill)

    goals = [
        make_model(Goal, description="Note in Mathe verbessern"),
        make_model(Goal, description="KI-Tools effektiver nutzen lernen"),
        make_model(Goal, description="Schulprojekte schneller abschließen"),
    ]
    for goal in goals:
        db.session.add(goal)

    tools = [
        make_model(
            Tool,
            name="Groq API (Llama 3)",
            category="KI-Textgenerierung",
            url="https://console.groq.com",
            notes="Sehr schnelle kostenlose Text-KI, ideal für Analysen und Schreiben"
        ),
        make_model(
            Tool,
            name="Stable Diffusion (DreamStudio)",
            category="Bilderstellung",
            url="https://dreamstudio.ai",
            notes="Kostenlose Credits für realistische KI-Bilder"
        ),
        make_model(
            Tool,
            name="Perplexity AI",
            category="Internet-Recherche",
            url="https://perplexity.ai",
            notes="KI-gestützte Suchmaschine mit Quellenangaben, kostenlos nutzbar"
        ),
        make_model(
            Tool,
            name="Zotero",
            category="Literaturverwaltung",
            url="https://zotero.org",
            notes="Kostenlose Literaturverwaltung für wissenschaftliche Arbeiten"
        ),
        make_model(
            Tool,
            name="Canva (Free)",
            category="Design & Präsentation",
            url="https://canva.com",
            notes="Kostenlose Designplattform für Präsentationen, Poster, Social Media"
        ),
        make_model(
            Tool,
            name="Anki",
            category="Lernen & Schule",
            url="https://apps.ankiweb.net",
            notes="Kostenlose Lernkarten-App mit intelligentem Wiederholungssystem"
        ),
        make_model(
            Tool,
            name="Wolfram Alpha",
            category="Mathe & Wissenschaft",
            url="https://wolframalpha.com",
            notes="Mächtiges Rechenwerkzeug für Mathematik, Physik, Chemie"
        ),
        make_model(
            Tool,
            name="DeepL",
            category="Übersetzung",
            url="https://deepl.com",
            notes="Hochqualitative kostenlose Übersetzungen"
        ),
        make_model(
            Tool,
            name="Bing Image Creator",
            category="Bilderstellung",
            url="https://www.bing.com/images/create",
            notes="Kostenlose KI-Bildgenerierung via DALL-E, kein Account nötig"
        ),
        make_model(
            Tool,
            name="NotebookLM",
            category="Recherche & Analyse",
            url="https://notebooklm.google.com",
            notes="Google-Tool zum Analysieren und Zusammenfassen von Dokumenten, kostenlos"
        ),
    ]
    for tool in tools:
        db.session.add(tool)

    db.session.commit()
    print("✅ Datenbank mit Beispieldaten befüllt.")
