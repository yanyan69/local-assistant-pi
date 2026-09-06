# ingest_dev_docs.py
import os
import shutil
import subprocess
import zipfile
import urllib.request
import re
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
BUILD_DIR = os.path.join(BASE_DIR, "build_tmp")
DB_PATH = os.path.join(BASE_DIR, "knowledge_base.db")


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


def populate_sqlite_database():
    """Reads `./knowledge_base/` and populates `knowledge_base.db` for FTS5 search."""
    print("[*] Indexing local files into SQLite database...")
    init_db()

    inserted_count = 0
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Clear existing records to prevent duplicates on re-run
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

                        if content:
                            cursor.execute("""
                                INSERT INTO paragraphs (filename, filepath, category, source_type, content)
                                VALUES (?, ?, ?, ?, ?)
                            """, (file, rel_path, category, "local_doc", content))
                            inserted_count += 1
                    except Exception as e:
                        print(f"[!] Error indexing {file}: {e}")

        conn.commit()

    print(f"[+] Successfully saved {inserted_count} files into `knowledge_base.db`.")


def cleanup():
    """Clean temporary archive files."""
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)


if __name__ == "__main__":
    prepare_directories()
    fetch_tldr_pages()
    dump_system_cli_help()
    fetch_awesome_cheatsheets()
    populate_sqlite_database()
    cleanup()
    print("\n[+] Ingestion complete! SQLite database updated at `./knowledge_base.db`.")