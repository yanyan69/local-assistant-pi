#server.py code for RPi 5, 4GB RAM
import os
import sys
import ctypes
import sqlite3
import re
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from flask import Flask, request, jsonify, render_template_string
from llama_cpp import Llama
from web_ui import get_chat_html
from robot import process_robot_request
from rank_bm25 import BM25Okapi

app = Flask(__name__)

@contextmanager
def silence_all_output():
    """Suppresses all low-level console logging (stdout and stderr) at the C-layer."""
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

MODEL_PATH = "./Llama-3.2-1B-Instruct.Q4_K_M.gguf"
DB_PATH = "knowledge_base.db"

print("[SYSTEM INFO]: Initializing Llama 3.2 engine safely...")
with silence_all_output():
        llm = Llama(
            model_path=MODEL_PATH, 
            n_ctx=2048, 
            n_threads=4, 
            n_batch=128, 
            verbose=False,
            loghandler=None
        )

if sys.platform == "win32":
    kernel32 = ctypes.windll.kernel32
    kernel32.SetStdHandle(-11, kernel32.GetStdHandle(-11))
    kernel32.SetStdHandle(-12, kernel32.GetStdHandle(-12))
    sys.stdout = open('CONOUT$', 'w', buffering=1)
    sys.stderr = open('CONOUT$', 'w', buffering=1)

print("[SYSTEM INFO]: Llama 3.2 engine is active and ready.")

# --- GLOBAL BM25 CORPUS IN-MEMORY INDEXING ---
print("[SYSTEM INFO]: Pre-indexing knowledge base via BM25...")

GLOBAL_ROWS = []
BM25_INDEX = None


def init_global_search_index():
    global GLOBAL_ROWS, BM25_INDEX

    if not os.path.exists(DB_PATH):
        print("[WARNING]: knowledge_base.db not found. Search fallback enabled.")
        return

    try:
        with sqlite3.connect(
            f"file:{DB_PATH}?mode=ro",
            uri=True
        ) as conn:

            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    id,
                    filename,
                    filepath,
                    category,
                    source_type,
                    content
                FROM paragraphs
            """)

            GLOBAL_ROWS = cursor.fetchall()

            if GLOBAL_ROWS:
                tokenized_corpus = [
                    row[5].lower().split()
                    for row in GLOBAL_ROWS
                ]

                BM25_INDEX = BM25Okapi(tokenized_corpus)

                print(
                    f"[SYSTEM INFO]: Indexed "
                    f"{len(GLOBAL_ROWS)} paragraph blocks successfully."
                )

            else:
                print("[WARNING]: Knowledge base table is empty.")

    except Exception as e:
        print(f"[CRITICAL INDEX ERROR]: {e}")


init_global_search_index()


def search_database(query, max_results=4):
    """Search the local knowledge base using BM25 with intent-based priority boosting."""
    if not BM25_INDEX or not GLOBAL_ROWS:
        return "No local document records available."

    # Words that signal the user wants an overview/basic concept
    overview_triggers = {"about", "what", "whatis", "definition", "meaning", "explain", "describe", "intro", "introduction", "basic", "basics"}
    
    instructional_words = overview_triggers.union({
        "tell", "your", "with", "this", "that", "from", "and", "how", "why", "does", "is"
    })

    raw_tokens = [term.lower() for term in query.split() if len(term) > 2]
    core_subjects = [token for token in raw_tokens if token not in instructional_words]

    if not core_subjects:
        core_subjects = raw_tokens

    if not raw_tokens:
        return "No clear search query detected."

    # Detect if user is asking for a general introduction
    is_overview_request = any(trigger in raw_tokens for trigger in overview_triggers)

    try:
        doc_scores = BM25_INDEX.get_scores(raw_tokens)

        # Zip scores with rows so we can manipulate the ranking safely
        scored_list = list(zip(doc_scores, GLOBAL_ROWS))
        boosted_scored_docs = []

        for score, row in scored_list:
            filename_lower = row[1].lower()
            category_lower = row[3].lower()
            
            # Apply an architectural "Boost" if the user wants general info
            # and the file or category looks like introductory material
            if is_overview_request:
                # Prioritize files with "intro", "summary", "guide", "wikipedia", or matching general names
                if any(k in filename_lower for k in ["intro", "summary", "guide", "wikipedia", "basic", "pocket"]):
                    score += 1.5  # Soft boost to pull introductory text to the top
                if any(k in category_lower for k in ["intro", "general", "documentation"]):
                    score += 1.0

            boosted_scored_docs.append((score, row))

        # Re-sort based on our new boosted scores
        scored_docs = sorted(boosted_scored_docs, key=lambda x: x[0], reverse=True)

        top_matches = []

        for score, row in scored_docs:
            if len(top_matches) >= max_results:
                break

            if score <= 2.5:  # Absolute baseline relevance threshold
                continue

            doc_text = row[5]
            doc_text_lower = doc_text.lower()

            has_core_subject = any(
                subject in doc_text_lower
                for subject in core_subjects
            )

            if not has_core_subject:
                continue

            filename = row[1]
            filepath = row[2]
            category = row[3]
            source_type = row[4]

            top_matches.append(
                f"[Source: {filename}]\n"
                f"[Path: {filepath}]\n"
                f"[Category: {category}]\n"
                f"[Type: {source_type}]\n"
                f"[Relevance Boosted Score: {score:.2f}]\n"
                f"{doc_text}"
            )

        if not top_matches:
            return "No highly relevant text matches found in local documents."

        return "\n\n---\n\n".join(top_matches)

    except Exception as e:
        print(f"[SEARCH ERROR]: {e}")
        return "Knowledge search error occurred."

BAD_WORDS_RE = re.compile(
    r'\b(fuck|fucking|fucked|slave|bitch|shit|damn)\b',
    re.IGNORECASE
)

#web_ui.py
@app.route('/', methods=['GET'])
def render_browser_interface():
    return render_template_string(get_chat_html())

#robot.py
@app.route('/api/robot', methods=['POST'])
def robot_endpoint():
    data = request.get_json()

    response, status = process_robot_request(
        data,
        llm,
        search_database
    )

    return jsonify(response), status

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)