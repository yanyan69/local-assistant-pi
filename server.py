import os
import sys
import ctypes
import sqlite3
import re
import json
import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

# Suppress Llama native logs via environment variables before import
os.environ["LLAMA_LOG_LEVEL"] = "ERROR"

from llama_cpp import Llama
from web_ui import get_chat_html
from robot import process_robot_request


MODEL_PATH = "./Llama-3.2-1B-Instruct.Q4_K_M.gguf"
DB_PATH = "knowledge_base.db"

# Global references
llm: Llama = None
llm_lock = asyncio.Lock()


# --- SILENCE C-LEVEL OUTPUT ---
@contextmanager
def silence_all_output():
    """Suppresses low-level C-layer logging during init."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stdout = os.dup(1)
    old_stderr = os.dup(2)
    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    try:
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(old_stdout, 1)
        os.dup2(old_stderr, 2)
        os.close(old_stdout)
        os.close(old_stderr)
        os.close(devnull)


# --- NATIVE SQLITE FTS5 SEARCH INDEXING ---
def init_fts5_index():
    """Configures SQLite native FTS5 full-text index with C-level BM25 scoring and auto-sync trigger."""
    if not os.path.exists(DB_PATH):
        print("[WARNING]: DB not found. Knowledge base search disabled.")
        return

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='paragraphs'")
            if not cursor.fetchone():
                print("[WARNING]: 'paragraphs' table does not exist in DB.")
                return

            # Create FTS5 virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS paragraphs_fts USING fts5(
                    id UNINDEXED,
                    filename,
                    filepath,
                    category,
                    source_type,
                    content,
                    tokenize='unicode61 remove_diacritics 1'
                );
            """)

            # Create automatic insertion trigger to eliminate expensive NOT IN sync checks
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS paragraphs_ai AFTER INSERT ON paragraphs BEGIN
                    INSERT INTO paragraphs_fts(id, filename, filepath, category, source_type, content)
                    VALUES (new.id, new.filename, new.filepath, new.category, new.source_type, new.content);
                END;
            """)

            # Perform initial backfill if needed
            cursor.execute("SELECT COUNT(*) FROM paragraphs_fts")
            fts_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM paragraphs")
            source_count = cursor.fetchone()[0]

            if fts_count < source_count:
                print(f"[SYSTEM INFO]: Indexing {source_count - fts_count} new entries into FTS5...")
                cursor.execute("""
                    INSERT INTO paragraphs_fts(id, filename, filepath, category, source_type, content)
                    SELECT id, filename, filepath, category, source_type, content 
                    FROM paragraphs 
                    WHERE id NOT IN (SELECT id FROM paragraphs_fts);
                """)
                conn.commit()
                print("[SYSTEM INFO]: FTS5 BM25 index fully populated.")
            else:
                print("[SYSTEM INFO]: FTS5 BM25 index up-to-date.")

    except Exception as e:
        print(f"[CRITICAL INDEX ERROR]: {e}")


def search_database(query: str, max_results: int = 4) -> str:
    """Executes zero-RAM native C-level BM25 search via SQLite FTS5."""
    if not os.path.exists(DB_PATH):
        return "No local document records available."

    sanitized_terms = re.findall(r'\w+', query.lower())
    stop_words = {"about", "what", "whatis", "explain", "describe", "intro", "tell", "your", "with", "this", "that", "from", "and", "how", "why", "does", "is"}
    core_terms = [term for term in sanitized_terms if len(term) > 2 and term not in stop_words]

    if not core_terms:
        core_terms = [term for term in sanitized_terms if len(term) > 2]

    if not core_terms:
        return "No clear search query detected."

    fts_match_query = " OR ".join(core_terms)

    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    filename,
                    filepath,
                    category,
                    source_type,
                    content,
                    bm25(paragraphs_fts) AS rank
                FROM paragraphs_fts
                WHERE paragraphs_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
            """, (fts_match_query, max_results))

            rows = cursor.fetchall()

            if not rows:
                return "No highly relevant text matches found in local documents."

            top_matches = []
            for row in rows:
                filename, filepath, category, source_type, content, rank = row
                # Filter out weak relevance scores (BM25 scores are negative in SQLite)
                if rank > -0.5:
                    continue
                top_matches.append(
                    f"[Source: {filename}]\n"
                    f"[Path: {filepath}]\n"
                    f"[Category: {category}]\n"
                    f"[Type: {source_type}]\n"
                    f"[BM25 Score: {abs(rank):.2f}]\n"
                    f"{content}"
                )

            return "\n\n---\n\n".join(top_matches) if top_matches else "No strong matches found."

    except Exception as e:
        print(f"[SEARCH ERROR]: {e}")
        return "Knowledge search error occurred."


# --- ASYNC LIFESPAN HANDLER (FastAPI startup/shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm
    print("[SYSTEM INFO]: Initializing Llama 3.2 engine safely on Raspberry Pi 5...")
    
    with silence_all_output():
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=2048,
            n_threads=4,       # Pi 5 Quad-core ARM Cortex-A76
            n_batch=512,       # Increased from 128 to 512 for faster prompt evaluation
            flash_attn=True,   # Speed up prompt evaluation and save RAM
            verbose=False,
            loghandler=None
        )

    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        kernel32.SetStdHandle(-11, kernel32.GetStdHandle(-11))
        kernel32.SetStdHandle(-12, kernel32.GetStdHandle(-12))
        sys.stdout = open('CONOUT$', 'w', buffering=1)
        sys.stderr = open('CONOUT$', 'w', buffering=1)

    print("[SYSTEM INFO]: Llama 3.2 engine active and ready.")
    init_fts5_index()
    
    yield
    
    print("[SYSTEM INFO]: Shutting down system.")


app = FastAPI(lifespan=lifespan)


# --- ROUTES ---
@app.get("/", response_class=HTMLResponse)
async def render_browser_interface():
    return HTMLResponse(content=get_chat_html())


@app.post("/api/robot")
async def robot_endpoint(request: Request):
    data = await request.json()

    async def event_stream() -> AsyncGenerator[str, None]:
        async with llm_lock:
            loop = asyncio.get_running_loop()
            
            # process_robot_request returns a tuple: (result_dict, status_code)
            result_dict, status_code = await loop.run_in_executor(
                None, 
                process_robot_request, 
                data, 
                llm, 
                search_database
            )
            
            # Unpack result_dict so history, response, and hardware_cmd are at the top level
            payload = {
                "response": result_dict.get("response", ""),
                "hardware_cmd": result_dict.get("hardware_cmd", "NONE"),
                "history": result_dict.get("history", []),
                "status": status_code
            }
            
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    # Direct app execution to prevent module loader errors
    uvicorn.run(app, host="0.0.0.0", port=5000, workers=1)