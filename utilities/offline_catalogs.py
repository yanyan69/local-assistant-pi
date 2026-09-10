"""Build and query local anime, game, and lifestyle catalogs."""

import argparse
import json
import sqlite3
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.app_config import DATA_DIR, KNOWLEDGE_BASE_DIR

CATALOG_DB_PATH = DATA_DIR / "offline_catalog.db"
CATALOG_DATABASE_DIR = DATA_DIR / "catalogs"
_READ_CONNECTIONS = {}
_READ_CONNECTIONS_LOCK = threading.Lock()
USER_AGENT = "local-assistant-pi/1.0"
JIKAN_BASE_URL = "https://api.jikan.moe/v4"
WIKIPEDIA_API_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
END_OF_LIFE_API_URL = "https://endoflife.date/api/"
REPOLOGY_API_URL = "https://repology.org/api/v1/project/"
JIKAN_GENRE_IDS = {"ecchi": 9, "hentai": 12}
LINUX_CATALOG_PATH = DATA_DIR.parent / "data" / "linux_catalog.json"

ANIME_SEEDS = [
    "Tengen Toppa Gurren Lagann", "Death Note", "No Game No Life",
    "Neon Genesis Evangelion", "Chainsaw Man", "Serial Experiments Lain",
    "Steins;Gate", "Code Geass", "Naruto", "Bleach", "One Piece",
    "JoJo's Bizarre Adventure", "Hunter x Hunter", "Cyberpunk: Edgerunners",
]

GAME_SEEDS = [
    "Elden Ring", "Mobile Legends: Bang Bang", "Sekiro: Shadows Die Twice",
    "Dead Cells", "Tekken", "Minecraft", "Wuthering Waves",
    "Black Myth: Wukong", "Blasphemous", "Bitburner", "Cyberpunk 2077",
]

GAME_WIKIPEDIA_PAGES = {
    "Blasphemous": "Blasphemous_(video_game)",
}

LINUX_REFERENCE_NOTES = {
    "Archinstall": (
        "# archinstall\n\n"
        "archinstall is the guided installer included in the official Arch Linux installation environment. "
        "Boot the official Arch installation medium, establish the required network and clock state, then run `archinstall` from the live environment. "
        "Review its current menus and configuration choices before committing changes; do not assume package names, disk layouts, or bootloader choices.\n\n"
        "Official documentation: https://wiki.archlinux.org/title/Archinstall\n"
    ),
    "CachyOS": (
        "# CachyOS\n\n"
        "CachyOS is an Arch-based Linux distribution with its own installation media, repositories, defaults, and kernel choices. "
        "Arch commands and documentation are not automatically interchangeable with CachyOS instructions. Prefer CachyOS documentation for installation, kernels, repositories, and hardware configuration.\n\n"
        "Official documentation: https://wiki.cachyos.org/\n"
    ),
}

LIFESTYLE_NOTES = {
    "lifestyle/fitness/exercises_by_muscle.md": """# Exercises by Muscle Group

Chest: push-up, bench press, dumbbell press, cable fly.
Back: pull-up, lat pulldown, row, deadlift.
Shoulders: overhead press, lateral raise, rear-delt fly.
Arms: curl, hammer curl, triceps pushdown, close-grip press.
Quadriceps: squat, split squat, lunge, leg press.
Glutes and hamstrings: hip thrust, Romanian deadlift, leg curl, step-up.
Calves: standing calf raise, seated calf raise.
Core: plank, side plank, dead bug, hanging knee raise.

Movement patterns: push, pull, squat, hinge, carry, brace. Progress by adding a small amount of repetitions, load, range of motion, or control while maintaining form. Stop for sharp or worsening pain and seek qualified advice.

Source note: local educational reference, not medical advice.
""",
    "lifestyle/fitness/training_concepts.md": """# Training Concepts

Progressive overload: gradually increase a training demand.
Volume: total work, commonly sets multiplied by repetitions and load.
Intensity: load or effort relative to ability; do not confuse it with volume.
Frequency: how often a muscle or movement is trained.
RIR: repetitions in reserve; an estimate of how many good repetitions remain.
Deload: a planned reduction in training stress for recovery.
Bulking: gaining mass with a sustained energy surplus.
Lean bulking: a smaller surplus intended to limit unnecessary fat gain.

Keep a simple log of exercise, sets, repetitions, load, effort, sleep, and pain. Individual programming depends on age, training history, health, equipment, and goals.

Source note: local educational reference, not medical advice.
""",
    "lifestyle/nutrition/macros_and_nutrients.md": """# Macros and Nutrients

Macronutrients: protein, carbohydrate, and fat. Micronutrients include vitamins and minerals. Water and fiber also matter for health and digestion.

Protein supports tissue maintenance and recovery; useful foods include eggs, dairy, meat, fish, legumes, tofu, and nuts. Carbohydrates are a useful fuel source; common sources include grains, fruit, potatoes, and legumes. Fat supports energy needs and helps absorb fat-soluble vitamins; common sources include oils, nuts, seeds, fish, and avocado.

Practical meal template: protein source + vegetables or fruit + carbohydrate or fat source + water. Labels and tracking apps are estimates; adjust using trends in energy, hunger, recovery, and performance.

Source note: local educational reference, not individualized nutrition or medical advice.
""",
    "lifestyle/nutrition/meal_planning.md": """# Meal Planning

Use a repeatable list of meals rather than trying to optimize every meal. Plan protein sources, produce, staple carbohydrates, healthy fats, water, and convenient options.

A simple day can include breakfast, lunch, dinner, and optional snacks. Batch-cook safely, label dates, refrigerate promptly, and follow local food-safety guidance. Dietary restrictions, allergies, medical conditions, and eating-disorder history require individualized professional guidance.

Source note: local educational reference, not medical advice.
""",
    "lifestyle/health/sleep_and_recovery.md": """# Sleep and Recovery

Useful habits: consistent sleep and wake times, morning light, a dark and quiet room, a wind-down routine, regular movement, and sensible caffeine timing.

Recovery is affected by sleep, nutrition, stress, illness, workload, and training volume. Persistent insomnia, breathing interruptions, severe daytime sleepiness, or concerning symptoms should be discussed with a qualified healthcare professional.

Source note: local educational reference, not medical advice.
""",
}


def connect(db_path: Path = CATALOG_DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            title TEXT NOT NULL,
            aliases TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL,
            source_url TEXT NOT NULL DEFAULT '',
            retrieved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(domain, title)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
            title, aliases, content, domain, source_url,
            content='documents', content_rowid='id'
        );
        CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
            INSERT INTO documents_fts(rowid, title, aliases, content, domain, source_url)
            VALUES (new.id, new.title, new.aliases, new.content, new.domain, new.source_url);
        END;
        CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, title, aliases, content, domain, source_url)
            VALUES ('delete', old.id, old.title, old.aliases, old.content, old.domain, old.source_url);
        END;
        CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
            INSERT INTO documents_fts(documents_fts, rowid, title, aliases, content, domain, source_url)
            VALUES ('delete', old.id, old.title, old.aliases, old.content, old.domain, old.source_url);
            INSERT INTO documents_fts(rowid, title, aliases, content, domain, source_url)
            VALUES (new.id, new.title, new.aliases, new.content, new.domain, new.source_url);
        END;
    """)
    return connection


def topic_database_path(domain: str) -> Path:
    safe_domain = domain.replace("/", "_").replace("\\", "_")
    return CATALOG_DATABASE_DIR / f"{safe_domain}.db"


def sync_topic_databases(source_db_path: Path = CATALOG_DB_PATH):
    """Materialize read-only topic databases from the importer master database."""
    if not source_db_path.exists():
        return
    CATALOG_DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_db_path) as source:
        domains = [row[0] for row in source.execute("SELECT DISTINCT domain FROM documents")]
        for domain in domains:
            destination = topic_database_path(domain)
            if destination.exists():
                destination.unlink()
            with sqlite3.connect(destination) as target:
                target.executescript("""
                    CREATE TABLE documents (
                        id INTEGER PRIMARY KEY, domain TEXT, title TEXT, aliases TEXT,
                        content TEXT, source_url TEXT, retrieved_at TEXT
                    );
                    CREATE VIRTUAL TABLE documents_fts USING fts5(
                        title, aliases, content, domain, source_url,
                        content='documents', content_rowid='id'
                    );
                """)
                rows = source.execute(
                    "SELECT id, domain, title, aliases, content, source_url, retrieved_at FROM documents WHERE domain = ?",
                    (domain,),
                ).fetchall()
                target.executemany("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
                target.execute("INSERT INTO documents_fts(documents_fts) VALUES ('rebuild')")
                target.commit()
    print(f"[+] Synchronized {len(domains)} topic catalog databases in `{CATALOG_DATABASE_DIR}`.")


def _read_connection(db_path: Path):
    key = str(db_path.resolve())
    with _READ_CONNECTIONS_LOCK:
        connection = _READ_CONNECTIONS.get(key)
        if connection is None:
            connection = sqlite3.connect(f"file:{key}?mode=ro", uri=True, check_same_thread=False)
            _READ_CONNECTIONS[key] = connection
        return connection


def close_catalog_connections():
    with _READ_CONNECTIONS_LOCK:
        for connection in _READ_CONNECTIONS.values():
            connection.close()
        _READ_CONNECTIONS.clear()


def request_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def request_repology_project(package: str):
    request = urllib.request.Request(
        REPOLOGY_API_URL + urllib.parse.quote(package, safe=""),
        headers={"User-Agent": "local-assistant-pi/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def load_linux_catalog() -> dict:
    with LINUX_CATALOG_PATH.open("r", encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)
    if not isinstance(catalog, dict):
        raise ValueError("Linux catalog must be an object")
    return catalog


def upsert_document(connection, domain: str, title: str, content: str, source_url: str, aliases: Iterable[str] = ()):
    connection.execute("""
        INSERT INTO documents(domain, title, aliases, content, source_url)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(domain, title) DO UPDATE SET
            aliases=excluded.aliases, content=excluded.content,
            source_url=excluded.source_url, retrieved_at=CURRENT_TIMESTAMP
    """, (domain, title, ", ".join(aliases), content, source_url))


def import_anime(connection):
    for seed in ANIME_SEEDS:
        try:
            query = urllib.parse.quote(seed, safe="")
            results = request_json(f"{JIKAN_BASE_URL}/anime?q={query}&limit=1").get("data", [])
            if not results:
                raise ValueError("Jikan returned no matching anime")
            anime_id = results[0]["mal_id"]
            details = request_json(f"{JIKAN_BASE_URL}/anime/{anime_id}/full").get("data", results[0])
            title = details.get("title") or seed
            genres = [item.get("name", "") for item in details.get("genres", [])]
            characters = request_json(f"{JIKAN_BASE_URL}/anime/{anime_id}/characters").get("data", [])
            character_names = [item.get("character", {}).get("name", "") for item in characters]
            content = (
                f"# {title}\n\nSynopsis: {details.get('synopsis') or 'No synopsis available.'}\n\n"
                f"Genres: {', '.join(genres) or 'Not listed'}\n\n"
                f"Studios: {', '.join(item.get('name', '') for item in details.get('studios', [])) or 'Not listed'}\n\n"
                f"Episodes: {details.get('episodes') or 'Unknown'}\n\n"
                f"Characters: {', '.join(character_names) or 'Not listed'}\n"
            )
            source_url = f"https://myanimelist.net/anime/{anime_id}"
            upsert_document(connection, "anime", title, content, source_url, [seed, *genres, *character_names])
            connection.commit()
            print(f"[+] Imported anime: {title}")
        except Exception as error:
            try:
                page = urllib.parse.quote(seed.replace(" ", "_"), safe="")
                api_url = WIKIPEDIA_API_URL + page
                data = request_json(api_url)
                title = data.get("title", seed)
                extract = data.get("extract", "").strip()
                source_url = data.get("content_urls", {}).get("desktop", {}).get("page", api_url)
                if not extract:
                    raise ValueError("Wikipedia returned no summary")
                upsert_document(connection, "anime", title, f"# {title}\n\n{extract}\n\nSource: Wikipedia, {source_url}\n", source_url, [seed])
                connection.commit()
                print(f"[+] Imported anime overview fallback: {title}")
            except Exception as fallback_error:
                print(f"[!] Anime import skipped for {seed}: {error}; fallback: {fallback_error}")


def import_anime_genre(connection, genre: str, pages: int = 2):
    """Import a bounded set of anime carrying a verified Jikan genre tag."""
    genre_id = JIKAN_GENRE_IDS[genre]
    for page_number in range(1, pages + 1):
        try:
            data = request_json(
                f"{JIKAN_BASE_URL}/anime?genres={genre_id}&page={page_number}&limit=25&sfw=false"
            )
            titles = data.get("data", [])
            if not titles:
                break
            for item in titles:
                title = item.get("title") or "Unknown title"
                synopsis = item.get("synopsis") or "No synopsis available."
                tags = [genre.title()]
                source_url = f"https://myanimelist.net/anime/{item['mal_id']}"
                content = (
                    f"# {title}\n\nGenre: {genre.title()}\n\n"
                    f"Synopsis: {synopsis}\n\n"
                    "This record was imported because the source tagged it with this genre. "
                    "Check the source rating and content warnings before recommending it.\n"
                )
                upsert_document(connection, "anime", title, content, source_url, [genre, *tags])
            connection.commit()
            print(f"[+] Imported {len(titles)} verified {genre} anime records from page {page_number}.")
        except Exception as error:
            print(f"[!] Could not import {genre} page {page_number}: {error}")
            break


def import_games(connection):
    for seed in GAME_SEEDS:
        page_name = GAME_WIKIPEDIA_PAGES.get(seed, seed.replace(" ", "_"))
        page = urllib.parse.quote(page_name, safe="")
        api_url = WIKIPEDIA_API_URL + page
        try:
            data = request_json(api_url)
            title = data.get("title", seed)
            extract = data.get("extract", "").strip()
            source_url = data.get("content_urls", {}).get("desktop", {}).get("page", api_url)
            if extract:
                if seed == "Blasphemous":
                    connection.execute("DELETE FROM documents WHERE domain = 'games' AND title = 'Blasphemy'")
                upsert_document(connection, "games", title, f"# {title}\n\n{extract}\n\nSource: Wikipedia, {source_url}\n", source_url, [seed])
                connection.commit()
                print(f"[+] Imported game reference: {title}")
        except Exception as error:
            print(f"[!] Game source unavailable for {seed}: {error}")


def import_lifestyle(connection, knowledge_base: Path):
    for relative_path, content in LIFESTYLE_NOTES.items():
        destination = knowledge_base / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        title = destination.stem.replace("_", " ").title()
        upsert_document(connection, "lifestyle", title, content, "local://lifestyle-notes")
        print(f"[+] Wrote lifestyle note: {relative_path}")


def import_linux(connection):
    """Import bounded distro lifecycle data and package ecosystem references."""
    catalog = load_linux_catalog()
    for distro in catalog.get("distributions", []):
        name = distro["name"]
        product = distro["product"]
        if not product:
            continue
        source_url = f"{END_OF_LIFE_API_URL}{urllib.parse.quote(product, safe='')}.json"
        try:
            releases = request_json(source_url)
            if not isinstance(releases, list):
                raise ValueError("lifecycle API returned an unexpected format")
            lines = [f"# {name}", "", "Release lifecycle data from endoflife.date:", ""]
            for release in releases[:12]:
                cycle = release.get("cycle", "unknown")
                eol = release.get("eol", "unknown")
                release_date = release.get("releaseDate", "unknown")
                lines.append(f"- Cycle {cycle}: released {release_date}; end of life {eol}")
            content = "\n".join(lines) + "\n\nVerify current details at the source URL before making upgrade decisions.\n"
            upsert_document(connection, "linux", name, content, source_url, [name, product])
            connection.commit()
            print(f"[+] Imported Linux lifecycle data: {name}")
        except Exception as error:
            print(f"[!] Linux lifecycle unavailable for {name}: {error}")

    for ecosystem in catalog.get("package_ecosystems", []):
        aliases = ecosystem.get("aliases", [])
        content = (
            f"# {ecosystem['name']}\n\n"
            f"Aliases and related terms: {', '.join(aliases)}.\n\n"
            "Use the package manager's official documentation and verify the distribution before running commands.\n"
        )
        upsert_document(connection, "linux", ecosystem["name"], content, "local://linux-package-ecosystems", aliases)
    connection.commit()
    print(f"[+] Imported {len(catalog.get('package_ecosystems', []))} Linux package ecosystems.")
    for title, content in LINUX_REFERENCE_NOTES.items():
        source_url = content.rsplit("Official documentation: ", 1)[-1].strip()
        aliases = [title.lower()]
        if title == "CachyOS":
            aliases.append("cachy os")
        upsert_document(connection, "linux", title, content, source_url, aliases)
    connection.commit()
    print(f"[+] Imported {len(LINUX_REFERENCE_NOTES)} Linux reference notes.")


def import_package(connection, package: str):
    """Import one package project from Repology; do not bulk-mirror repositories."""
    records = request_repology_project(package)
    if not isinstance(records, list) or not records:
        print(f"[!] Repology returned no records for package: {package}")
        return
    lines = [f"# Package: {package}", "", "Repository records from Repology:", ""]
    aliases = [package]
    for record in records:
        repo = record.get("repo", "unknown")
        version = record.get("version", "unknown")
        summary = record.get("summary", "")
        licenses = ", ".join(record.get("licenses", [])) or "not listed"
        lines.append(f"- {repo}: {version}; license: {licenses}; {summary}".rstrip())
        aliases.extend([record.get("binname", ""), record.get("srcname", "")])
    content = "\n".join(lines) + "\n\nVerify repository-specific instructions before installing packages.\n"
    upsert_document(connection, "linux/packages", package, content, REPOLOGY_API_URL + urllib.parse.quote(package, safe=""), aliases)
    connection.commit()
    print(f"[+] Imported package metadata: {package} ({len(records)} repository records)")


def rebuild_fts(connection):
    connection.execute("INSERT INTO documents_fts(documents_fts) VALUES ('rebuild')")
    connection.commit()


def query_catalog(query: str, top_k: int = 4, db_path: Path = None, category: str = None) -> str:
    terms = [term for term in query.lower().split() if len(term) > 2]
    if not terms:
        return ""
    if db_path:
        paths = [db_path]
    elif category and topic_database_path(category).exists():
        paths = [topic_database_path(category)]
    else:
        paths = sorted(CATALOG_DATABASE_DIR.glob("*.db")) if CATALOG_DATABASE_DIR.exists() else [CATALOG_DB_PATH]
    rows = []
    for path in paths:
        if not path.exists():
            continue
        connection = _read_connection(path)
        rows.extend(connection.execute(
            "SELECT title, domain, content, source_url FROM documents_fts WHERE documents_fts MATCH ? ORDER BY bm25(documents_fts) LIMIT ?",
            (" OR ".join(terms), top_k),
        ).fetchall())
    rows = rows[:top_k]
    return "\n\n---\n\n".join(
        f"[Catalog source: {title}]\n[Category: {domain}]\n{content}\nSource: {source_url}"
        for title, domain, content, source_url in rows
    )


def main():
    parser = argparse.ArgumentParser(description="Populate local catalogs; runtime searches never use the network.")
    parser.add_argument("--anime", action="store_true")
    parser.add_argument("--ecchi", action="store_true", help="Import a bounded set of Jikan-tagged ecchi anime.")
    parser.add_argument("--hentai", action="store_true", help="Import a bounded set of Jikan-tagged hentai anime.")
    parser.add_argument("--games", action="store_true")
    parser.add_argument("--linux", action="store_true", help="Import Linux distribution lifecycle and package ecosystem data.")
    parser.add_argument("--package", action="append", default=[], help="Import one package project from Repology; repeat for more packages.")
    parser.add_argument("--lifestyle", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not (args.anime or args.ecchi or args.hentai or args.games or args.linux or args.lifestyle or args.package or args.all):
        parser.error("choose --anime, --ecchi, --hentai, --games, --linux, --lifestyle, --package, or --all")
    connection = connect()
    try:
        if args.anime or args.all:
            import_anime(connection)
        if args.ecchi or args.all:
            import_anime_genre(connection, "ecchi")
        if args.hentai or args.all:
            import_anime_genre(connection, "hentai")
        if args.games or args.all:
            import_games(connection)
        if args.linux or args.all:
            import_linux(connection)
        for package in args.package:
            import_package(connection, package)
        if args.lifestyle or args.all:
            import_lifestyle(connection, KNOWLEDGE_BASE_DIR)
        rebuild_fts(connection)
        sync_topic_databases()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
