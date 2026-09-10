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
import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from core.app_config import BUILD_DIR as CONFIG_BUILD_DIR, KNOWLEDGE_BASE_DIR, KNOWLEDGE_DB_PATH

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KB_DIR = str(KNOWLEDGE_BASE_DIR)
BUILD_DIR = str(CONFIG_BUILD_DIR)
DB_PATH = str(KNOWLEDGE_DB_PATH)
KB_PATH = Path(KB_DIR).resolve()
SOURCES_DIR = KB_PATH / "sources"
SOURCE_MANIFEST_PATH = SOURCES_DIR / "manifest.json"
SOURCE_METADATA_DIR = SOURCES_DIR / "metadata"
MAX_SOURCE_BYTES = 25 * 1024 * 1024


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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS index_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        conn.commit()


def download_file(url: str, dest_path: str):
    """Helper to download files using custom headers to avoid GitHub blocking."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, 'wb') as out_file:
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_SOURCE_BYTES:
                raise ValueError(f"download exceeds {MAX_SOURCE_BYTES} byte limit")
            out_file.write(chunk)


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
        out_tldr = os.path.join(KB_DIR, "linux", "commands", "tldr")
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


def dump_linux_cli_help():
    """Extract help outputs directly from installed software on Pi."""
    print("[*] Generating offline manuals for installed system tools...")
    out_sys = os.path.join(KB_DIR, "linux", "commands", "manuals")
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
    out_cheat = os.path.join(KB_DIR, "programming", "cheatsheets")
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


def load_source_manifest():
    if not SOURCE_MANIFEST_PATH.exists():
        print(f"[!] Source manifest not found: {SOURCE_MANIFEST_PATH}")
        return []
    with SOURCE_MANIFEST_PATH.open("r", encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    sources = manifest.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("manifest field 'sources' must be a list")
    return sources


def source_metadata_path(source_id):
    safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", source_id)
    return SOURCE_METADATA_DIR / f"{safe_id}.json"


def source_destination(source):
    destination = (KB_PATH / source.get("destination", "")).resolve()
    if destination == KB_PATH or KB_PATH not in destination.parents:
        raise ValueError("destination must stay inside knowledge_base")
    return destination


def source_is_allowed(source):
    hostname = urlparse(source.get("url", "")).hostname
    allowed_domains = source.get("allowed_domains", [])
    return bool(hostname and hostname in allowed_domains)


def source_is_due(source, destination):
    if not destination.exists() or source.get("refresh", "never") == "never":
        return not destination.exists()
    metadata_path = source_metadata_path(source["id"])
    if not metadata_path.exists():
        return True
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        retrieved_at = datetime.fromisoformat(metadata["retrieved_at"])
        age_days = (datetime.now(timezone.utc) - retrieved_at).days
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return True
    refresh_days = {"daily": 1, "weekly": 7, "monthly": 30}.get(source["refresh"])
    return refresh_days is not None and age_days >= refresh_days


def write_source_metadata(source, destination, actual_url):
    metadata = {
        "source_id": source["id"],
        "url": actual_url,
        "destination": source["destination"],
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "attribution": source.get("attribution", ""),
        "license": source.get("license", ""),
    }
    SOURCE_METADATA_DIR.mkdir(parents=True, exist_ok=True)
    source_metadata_path(source["id"]).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def fetch_manifest_sources(force=False):
    """Download only approved manifest sources and record provenance metadata."""
    print("[*] Fetching approved manifest sources...")
    downloaded = 0
    skipped = 0
    seen_ids = set()
    for source in load_source_manifest():
        source_id = source.get("id")
        try:
            if not source_id or source_id in seen_ids:
                raise ValueError("source id is missing or duplicated")
            seen_ids.add(source_id)
            destination = source_destination(source)
            kind = source.get("kind")
            if kind == "url" and not source_is_allowed(source):
                raise ValueError("URL domain is not in allowed_domains")
            if kind not in {"url", "wikipedia_summary"}:
                raise ValueError(f"unsupported source kind: {kind}")
            if not force and not source_is_due(source, destination):
                skipped += 1
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            actual_url = source.get("url")
            if kind == "wikipedia_summary":
                page = urllib.parse.quote(source["page"], safe="")
                actual_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{page}"
                request = urllib.request.Request(actual_url, headers={"User-Agent": "local-assistant-pi/1.0"})
                with urllib.request.urlopen(request, timeout=15) as response:
                    data = json.load(response)
                extract = data.get("extract", "").strip()
                actual_url = data.get("content_urls", {}).get("desktop", {}).get("page", actual_url)
                if not extract:
                    raise ValueError("source returned no extract")
                content = (
                    f"# {data.get('title', source['page'].replace('_', ' '))}\n\n{extract}\n\n"
                    f"## Source and license\n\nSource: Wikipedia, {actual_url}\n"
                    f"{source.get('license', '')}\n"
                )
                destination.write_text(content, encoding="utf-8")
            else:
                download_file(actual_url, str(destination))
                content = destination.read_text(encoding="utf-8", errors="ignore")
                destination.write_text(
                    f"Source: {source.get('attribution', '')}\nURL: {actual_url}\n\n{content}",
                    encoding="utf-8",
                )
            write_source_metadata(source, destination, actual_url)
            downloaded += 1
            print(f"[+] Updated manifest source: {source_id}")
        except Exception as error:
            print(f"[x] Failed manifest source {source_id or '<unknown>'}: {error}")
    print(f"[+] Manifest sources updated: {downloaded}; skipped: {skipped}.")


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
    """Reads the configured knowledge directory and rebuilds SQLite paragraph and FTS5 indexes."""
    print("[*] Indexing local files into SQLite database...")
    init_db()

    inserted_count = 0
    content_digest = hashlib.sha256()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Rebuild from the files on disk so removed or edited documents stay accurate.
        cursor.execute("DELETE FROM paragraphs;")

        for root, _, files in os.walk(KB_DIR):
            relative_root = os.path.relpath(root, KB_DIR).replace("\\", "/")
            category = "" if relative_root == "." else relative_root
            for file in files:
                if file.endswith((".md", ".txt")):
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath, KB_DIR).replace("\\", "/")
                    
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read().strip()

                        if not content:
                            continue

                        content_digest.update(rel_path.encode("utf-8"))
                        content_digest.update(content.encode("utf-8", errors="ignore"))

                        for chunk_number, chunk in enumerate(split_document(content), start=1):
                            chunk_path = f"{rel_path}#section-{chunk_number}"
                            cursor.execute("""
                                INSERT INTO paragraphs (filename, filepath, category, source_type, content)
                                VALUES (?, ?, ?, ?, ?)
                            """, (file, chunk_path, category, "local_doc", chunk))
                            inserted_count += 1
                    except Exception as e:
                        print(f"[!] Error indexing {file}: {e}")

        cursor.execute(
            "INSERT OR REPLACE INTO index_metadata(key, value) VALUES (?, ?)",
            ("content_hash", content_digest.hexdigest()),
        )
        cursor.execute(
            "INSERT OR REPLACE INTO index_metadata(key, value) VALUES (?, ?)",
            ("index_version", datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    print(f"[+] Successfully saved {inserted_count} files into `{DB_PATH}`.")
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
    parser = argparse.ArgumentParser(description="Download approved sources and rebuild the local knowledge index.")
    parser.add_argument("--force", action="store_true", help="Refresh manifest sources even when their policy says they are not due.")
    args = parser.parse_args()
    prepare_directories()
    fetch_tldr_pages()
    dump_linux_cli_help()
    fetch_awesome_cheatsheets()
    fetch_manifest_sources(force=args.force)
    populate_sqlite_database()
    cleanup()
    print(f"\n[+] Ingestion complete! SQLite database updated at `{DB_PATH}`.")