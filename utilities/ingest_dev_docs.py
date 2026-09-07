# ingest_dev_docs.py
import os
import shutil
import subprocess
import zipfile
import urllib.request
import urllib.parse
import json
import re
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
BUILD_DIR = os.path.join(BASE_DIR, "build_tmp")
DB_PATH = os.path.join(BASE_DIR, "data", "knowledge_base.db")


def prepare_directories():
    """Ensure output directories exist."""
    os.makedirs(KB_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)


def init_db():
    """Ensure SQLite schema exists for paragraph storage."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                filepath TEXT,
                category TEXT,
                source_type TEXT,
                content TEXT
            );
        """)
        conn.commit()


def download_file(url: str, dest_path: str):
    """Helper to download files using custom headers to avoid GitHub blocking."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)


def fetch_tldr_pages():
    """Download and extract open-source tldr-pages repository."""
    print("[*] Fetching tldr-pages repository...")
    url = "https://github.com/tldr-pages/tldr/archive/refs/heads/main.zip"
    zip_path = os.path.join(BUILD_DIR, "tldr.zip")
    extract_path = os.path.join(BUILD_DIR, "tldr_extracted")

    try:
        download_file(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        tldr_pages_dir = os.path.join(extract_path, "tldr-main", "pages")
        out_tldr = os.path.join(KB_DIR, "tldr_commands")
        os.makedirs(out_tldr, exist_ok=True)

        count = 0
        # Valid platforms in official tldr repo: common, linux, osx, windows
        for platform in ["common", "linux"]:
            p_dir = os.path.join(tldr_pages_dir, platform)
            if not os.path.exists(p_dir):
                continue
            for file_name in os.listdir(p_dir):
                if file_name.endswith(".md"):
                    src = os.path.join(p_dir, file_name)
                    dest = os.path.join(out_tldr, f"{platform}_{file_name}")
                    shutil.copyfile(src, dest)
                    count += 1

        print(f"[+] Ingested {count} tldr command sheets.")
    except Exception as e:
        print(f"[x] Failed to fetch tldr-pages: {e}")


def dump_system_cli_help():
    """Extract help outputs directly from installed software on Pi."""
    print("[*] Generating offline manuals for installed system tools...")
    out_sys = os.path.join(KB_DIR, "system_cli")
    os.makedirs(out_sys, exist_ok=True)

    tools = [
        "git", "ffmpeg", "tar", "grep", "awk", "sed", "find", 
        "systemctl", "journalctl", "curl", "docker", "pip", 
        "python3", "gcc", "g++", "make", "sqlite3", "rsync",
        "ssh", "cron", "iptables", "netstat", "htop"
    ]

    count = 0
    for tool in tools:
        if not shutil.which(tool):
            continue
        try:
            res = subprocess.run([tool, "--help"], capture_output=True, text=True, timeout=3)
            output = res.stdout if res.stdout else res.stderr
            if output and len(output.strip()) > 50:
                filepath = os.path.join(out_sys, f"{tool}_help.md")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"# System Tool Manual: {tool}\n\n```text\n{output.strip()}\n```\n")
                count += 1
        except Exception:
            continue

    print(f"[+] Generated {count} local system command manuals.")


def fetch_awesome_cheatsheets():
    """Download programming cheatsheets from live mirror."""
    print("[*] Fetching programming & Linux cheatsheets...")
    out_cheat = os.path.join(KB_DIR, "cheatsheets")
    os.makedirs(out_cheat, exist_ok=True)

    # Active LeCoupa mirror URL
    url = "https://github.com/LeCoupa/awesome-cheatsheets/archive/refs/heads/master.zip"
    zip_path = os.path.join(BUILD_DIR, "cheatsheets.zip")
    extract_path = os.path.join(BUILD_DIR, "cheat_extracted")

    try:
        download_file(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        root = os.path.join(extract_path, "awesome-cheatsheets-master")
        count = 0
        for dirpath, _, filenames in os.walk(root):
            for file in filenames:
                if file.endswith((".md", ".txt")):
                    src = os.path.join(dirpath, file)
                    clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', file)
                    dest = os.path.join(out_cheat, clean_name)
                    shutil.copyfile(src, dest)
                    count += 1

        print(f"[+] Ingested {count} programming cheatsheets.")
    except Exception as e:
        print(f"[x] Failed to fetch cheatsheets: {e}")


def fetch_open_knowledge_sources():
    """Download small, attributed public-domain and Wikimedia reference sources."""
    print("[*] Fetching open general-knowledge sources...")

    gutenberg_sources = {
        "philosophy/meditations.txt": (
            "https://www.gutenberg.org/files/2680/2680-0.txt",
            "Project Gutenberg eBook 2680 - Meditations by Marcus Aurelius."
        ),
        "anime_scifi/frankenstein.txt": (
            "https://www.gutenberg.org/files/84/84-0.txt",
            "Project Gutenberg eBook 84 - Frankenstein by Mary Shelley."
        ),
    }

    for relative_path, (url, attribution) in gutenberg_sources.items():
        destination = os.path.join(KB_DIR, relative_path)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        if os.path.exists(destination):
            continue
        try:
            download_file(url, destination)
            with open(destination, "r+", encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
                handle.seek(0)
                handle.write(f"Source: {attribution}\nURL: {url}\n\n{content}")
                handle.truncate()
            print(f"[+] Downloaded {relative_path}.")
        except Exception as error:
            print(f"[x] Failed to download {relative_path}: {error}")

    wikipedia_pages = {
        "cooking/cooking_reference.md": "Cooking",
        "philosophy/stoicism_reference.md": "Stoicism",
        "anime_scifi/anime_reference.md": "Anime",
        "anime_scifi/science_fiction_reference.md": "Science_fiction",
    }

    for relative_path, page in wikipedia_pages.items():
        destination = os.path.join(KB_DIR, relative_path)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        if os.path.exists(destination):
            continue
        encoded_page = urllib.parse.quote(page, safe="")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_page}"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "local-assistant-pi/1.0"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.load(response)
            extract = data.get("extract", "").strip()
            source_url = data.get("content_urls", {}).get("desktop", {}).get("page", url)
            if extract:
                with open(destination, "w", encoding="utf-8") as handle:
                    handle.write(
                        f"# {data.get('title', page.replace('_', ' '))}\n\n"
                        f"{extract}\n\n"
                        "## Source and license\n\n"
                        f"Source: Wikipedia, {source_url}\n"
                        "Content is available under the applicable Wikimedia Commons/Wikipedia license.\n"
                    )
                print(f"[+] Downloaded {relative_path}.")
        except Exception as error:
            print(f"[x] Failed to download {relative_path}: {error}")


def split_document(content: str, max_chars: int = 2400):
    """Split long Markdown or text files into focused searchable chunks."""
    sections = re.split(r"(?=^#{1,6}\s+)", content, flags=re.MULTILINE)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        paragraphs = re.split(r"\n\s*\n", section)
        current = ""
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            while len(paragraph) > max_chars:
                split_at = paragraph.rfind(" ", 0, max_chars)
                split_at = split_at if split_at > 0 else max_chars
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(paragraph[:split_at].strip())
                paragraph = paragraph[split_at:].strip()
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if current and len(candidate) > max_chars:
                chunks.append(current)
                current = paragraph
            else:
                current = candidate
        if current:
            chunks.append(current)
    return chunks or [content.strip()]


def populate_sqlite_database():
    """Reads `./knowledge_base/` and rebuilds the SQLite paragraph and FTS5 indexes."""
    print("[*] Indexing local files into SQLite database...")
    init_db()

    inserted_count = 0
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Rebuild from the files on disk so removed or edited documents stay accurate.
        cursor.execute("DELETE FROM paragraphs;")

        for root, _, files in os.walk(KB_DIR):
            category = os.path.basename(root)
            for file in files:
                if file.endswith((".md", ".txt")):
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath, KB_DIR).replace("\\", "/")
                    
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read().strip()

                        if not content:
                            continue

                        for chunk_number, chunk in enumerate(split_document(content), start=1):
                            chunk_path = f"{rel_path}#section-{chunk_number}"
                            cursor.execute("""
                                INSERT INTO paragraphs (filename, filepath, category, source_type, content)
                                VALUES (?, ?, ?, ?, ?)
                            """, (file, chunk_path, category, "local_doc", chunk))
                            inserted_count += 1
                    except Exception as e:
                        print(f"[!] Error indexing {file}: {e}")

        conn.commit()

    print(f"[+] Successfully saved {inserted_count} files into `data/knowledge_base.db`.")
    rebuild_fts_index()


def rebuild_fts_index():
    """Recreate FTS5 after rebuilding paragraphs so deleted documents cannot remain searchable."""
    print("[*] Rebuilding FTS5 search index...")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TRIGGER IF EXISTS paragraphs_ai;")
        cursor.execute("DROP TABLE IF EXISTS paragraphs_fts;")
        cursor.execute("""
            CREATE VIRTUAL TABLE paragraphs_fts USING fts5(
                id UNINDEXED,
                filename,
                filepath,
                category,
                source_type,
                content,
                tokenize='unicode61 remove_diacritics 1'
            );
        """)
        cursor.execute("""
            INSERT INTO paragraphs_fts(id, filename, filepath, category, source_type, content)
            SELECT id, filename, filepath, category, source_type, content
            FROM paragraphs;
        """)
        cursor.execute("""
            CREATE TRIGGER paragraphs_ai AFTER INSERT ON paragraphs BEGIN
                INSERT INTO paragraphs_fts(id, filename, filepath, category, source_type, content)
                VALUES (new.id, new.filename, new.filepath, new.category, new.source_type, new.content);
            END;
        """)
        conn.commit()

    print("[+] FTS5 index rebuilt successfully.")


def cleanup():
    """Clean temporary archive files."""
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)


if __name__ == "__main__":
    prepare_directories()
    fetch_tldr_pages()
    dump_system_cli_help()
    fetch_awesome_cheatsheets()
    fetch_open_knowledge_sources()
    populate_sqlite_database()
    cleanup()
    print("\n[+] Ingestion complete! SQLite database updated at `./data/knowledge_base.db`.")