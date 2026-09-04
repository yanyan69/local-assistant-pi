import os
import sqlite3
from pypdf import PdfReader

DATA_DIR = "./my_source_files"
DB_PATH = "knowledge_base.db"


def init_db():
    """Remove and rebuild the knowledge database."""
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"[CLEANUP] Removed existing '{DB_PATH}'.")
        except Exception as e:
            print(f"[WARNING] Could not delete database: {e}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE paragraphs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            filepath TEXT,
            category TEXT,
            source_type TEXT,
            content TEXT
        )
    """)
    cursor.execute("""
        CREATE INDEX idx_category
        ON paragraphs(category)
    """)

    cursor.execute("""
        CREATE INDEX idx_source_type
        ON paragraphs(source_type)
    """)

    conn.commit()
    conn.close()


def chunk_text_by_structure(text, max_chars=350):
    """Split text into chunks while preserving paragraph, list, and table structures."""
    text = text.replace("−", "-").replace("—", " - ")
    raw_lines = text.split("\n")

    chunks = []
    current_chunk_lines = []
    current_len = 0

    for line in raw_lines:
        line = line.strip()

        if not line:
            if current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = []
                current_len = 0
            continue

        line_len = len(line)
        separator_len = 1 if current_chunk_lines else 0

        if current_len + separator_len + line_len <= max_chars:
            current_chunk_lines.append(line)
            current_len += separator_len + line_len
            continue

        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))
            current_chunk_lines = []
            current_len = 0

        if line_len <= max_chars:
            current_chunk_lines = [line]
            current_len = line_len
            continue

        # Safely split strings longer than max_chars without causing infinite loops
        remaining = line
        while len(remaining) > max_chars:
            split_at = remaining.rfind(" ", 0, max_chars)

            if split_at <= 0:
                split_at = max_chars

            # Append the cleaned slice
            chunks.append(remaining[:split_at].strip())
            
            # Slice strictly by position first to force physical loop progression
            remaining = remaining[split_at:] 
            
        # Clean up any leftover characters at the very end of the line
        remaining = remaining.strip()
        if remaining:
            current_chunk_lines = [remaining]
            current_len = len(remaining)

    if current_chunk_lines:
        chunks.append("\n".join(current_chunk_lines))

    return chunks



def extract_text_from_pdf(pdf_path):
    """Extract text from every page of a PDF."""
    text = ""

    try:
        reader = PdfReader(pdf_path)

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    except Exception as e:
        print(f"[PDF ERROR] {pdf_path}: {e}")

    return text


def get_source_info(filepath):
    """Determine category and source type from the file path."""
    relative_path = os.path.relpath(filepath, DATA_DIR)
    parts = relative_path.split(os.sep)

    filename = parts[-1]

    if len(parts) > 1:
        category = parts[0]
    else:
        category = "uncategorized"

    if filename.startswith("Wikipedia-"):
        source_type = "wikipedia"
    else:
        source_type = "technical_document"

    return filename, relative_path, category, source_type


def build_database():
    init_db()

    if not os.path.exists(DATA_DIR):
        print(f"[ERROR] Directory '{DATA_DIR}' not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Starting recursive document ingestion...")
    print(f"Source directory: {DATA_DIR}\n")

    total_files = 0
    total_chunks = 0

    for root, _, files in os.walk(DATA_DIR):

        for filename in files:
            if not filename.lower().endswith((".txt", ".md", ".pdf")):
                continue

            filepath = os.path.join(root, filename)

            filename, relative_path, category, source_type = \
                get_source_info(filepath)

            print(f"[{category}] {filename}")

            raw_content = ""

            if filename.lower().endswith((".txt", ".md")):
                try:
                    with open(
                        filepath,
                        "r",
                        encoding="utf-8",
                        errors="ignore"
                    ) as f:
                        raw_content = f.read()

                except Exception as e:
                    print(f"[TEXT ERROR] {filepath}: {e}")
                    continue

            elif filename.lower().endswith(".pdf"):
                print(f"  Parsing PDF...")
                raw_content = extract_text_from_pdf(filepath)

            if not raw_content.strip():
                print("  Skipped: no extractable text.")
                continue

            chunks = chunk_text_by_structure(raw_content)

            file_chunks = 0

            for chunk in chunks:
                # Strip boundary spaces, but preserve internal newlines
                cleaned_chunk = chunk.strip()

                if len(cleaned_chunk) <= 10:
                    continue

                cursor.execute(
                    """
                    INSERT INTO paragraphs
                    (filename, filepath, category, source_type, content)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        filename,
                        relative_path,
                        category,
                        source_type,
                        cleaned_chunk
                    )
                )
                file_chunks += 1
                total_chunks += 1

            total_files += 1

            print(f"  Added {file_chunks} chunks.")

    conn.commit()

    cursor.execute("VACUUM")

    conn.close()

    print("\n================================")
    print("INGESTION COMPLETE")
    print("================================")
    print(f"Files processed: {total_files}")
    print(f"Total chunks:    {total_chunks}")
    print(f"Database:        {DB_PATH}")


if __name__ == "__main__":
    build_database()