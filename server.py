import os
import sys
import ctypes
import sqlite3
import re
import json
import asyncio
import shlex
import subprocess
import time
import threading
import socket
import queue
from typing import AsyncGenerator
from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Suppress Llama native logs via environment variables before import
os.environ["LLAMA_LOG_LEVEL"] = "ERROR"

from llama_cpp import Llama
from web_ui import get_chat_html
from robot import process_robot_request
from core.app_config import (
    JELLYFIN_TOKEN,
    JELLYFIN_URL,
    JELLYFIN_ENABLED,
    KNOWLEDGE_DB_PATH,
    MEDIA_DIR,
    MODEL_PATH as CONFIG_MODEL_PATH,
    SERVER_PORT as CONFIG_SERVER_PORT,
    VOICE_ENABLED,
    TTS_ENABLED,
    build_runtime_config,
    config_value,
    load_settings,
)
from utilities.offline_catalogs import query_catalog
from core.local_memory import LocalMemoryStore
from core.conversations import ConversationStore
from robot import ROBOT_NAME, PERSONA_AVATAR
from core.system_context import read_system_context
from core.tools import TOOL_SCHEMAS, execute_tool
from core.backup import create_state_backup
from hardware.hardware_manager import hw_manager
from voice.transcriber import WhisperCppTranscriber
from voice.tts import PiperSynthesizer


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = str(CONFIG_MODEL_PATH)
DB_PATH = str(KNOWLEDGE_DB_PATH)
RUNTIME_CONFIG = build_runtime_config(str(config_value("MODE", "balanced", ["LOCAL_ASSISTANT_MODE"])))
SERVER_PORT = CONFIG_SERVER_PORT
SETTINGS = RUNTIME_CONFIG["settings"]
PROACTIVE_STATE = {"last_key": None}
METRICS_LOCK = threading.Lock()
METRICS = {
    "requests": 0,
    "completed": 0,
    "errors": 0,
    "last_latency_ms": 0.0,
    "average_latency_ms": 0.0,
    "last_response_chars": 0,
    "model_load_ms": 0.0,
}

# Global references
llm: Llama = None
llm_lock = asyncio.Lock()
memory_store = LocalMemoryStore(RUNTIME_CONFIG["memory_db_path"])
conversation_store = ConversationStore()
voice_transcriber = None
tts_synthesizer = None
voice_backend_lock = threading.Lock()


def get_voice_transcriber():
    global voice_transcriber
    if voice_transcriber is None and VOICE_ENABLED:
        with voice_backend_lock:
            if voice_transcriber is None:
                voice_transcriber = WhisperCppTranscriber()
    return voice_transcriber


def get_tts_synthesizer():
    global tts_synthesizer
    if tts_synthesizer is None and TTS_ENABLED:
        with voice_backend_lock:
            if tts_synthesizer is None:
                tts_synthesizer = PiperSynthesizer()
    return tts_synthesizer
voice_operation_lock = threading.Lock()


def is_allowed_command(command: str) -> bool:
    safe_cmd = (command or "").strip()
    if not safe_cmd:
        return False

    if any(token in safe_cmd for token in [";", "&&", "||", "|", ">", "<", "\n", "\r"]):
        return False

    try:
        parsed = shlex.split(safe_cmd)
    except ValueError:
        return False
    if not parsed or parsed[0].lower() in {"sudo", "rm", "mv", "cp", "chmod", "chown", "shutdown", "reboot", "poweroff"}:
        return False

    allowlist = RUNTIME_CONFIG["automation_allowlist"]
    return any(safe_cmd == allowed or safe_cmd.startswith(f"{allowed} ") for allowed in allowlist)


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", int(port)))
        except OSError:
            return False
    return True


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


COMMAND_TERMS = {
    "adb", "apt", "awk", "cat", "chmod", "chown", "cp", "curl", "docker", "ffmpeg",
    "find", "gcc", "g++", "git", "grep", "htop", "journalctl", "make", "mv", "pip",
    "python", "rsync", "scp", "sed", "ssh", "systemctl", "tar", "vim", "wget"
}


def search_database(query: str, max_results: int = 4, category: str = None) -> str:
    """Executes zero-RAM native C-level BM25 search via SQLite FTS5."""
    catalog_result = query_catalog(query, top_k=max_results, category=category)
    if not os.path.exists(DB_PATH):
        return catalog_result or "No local document records available."

    sanitized_terms = re.findall(r'\w+', query.lower())
    stop_words = {"about", "what", "whatis", "explain", "describe", "intro", "tell", "your", "with", "this", "that", "from", "and", "how", "why", "does", "is"}
    core_terms = [term for term in sanitized_terms if (len(term) > 2 or term in COMMAND_TERMS) and term not in stop_words]

    if not core_terms:
        core_terms = [term for term in sanitized_terms if len(term) > 2 or term in COMMAND_TERMS]

    if not core_terms:
        return "No clear search query detected."

    search_queries = [
        f'"{query.strip()}"',
        " AND ".join(core_terms),
        " OR ".join(core_terms),
    ]

    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
            cursor = conn.cursor()

            category_filter = " AND (category = ? OR category LIKE ? || '/%')" if category else ""
            sql = f"""
                SELECT 
                    filename,
                    filepath,
                    category,
                    source_type,
                    content,
                    bm25(paragraphs_fts) AS rank
                FROM paragraphs_fts
                WHERE paragraphs_fts MATCH ?{category_filter}
                ORDER BY rank ASC
                LIMIT ?
            """
            params = (fts_match_query, category, category, max_results) if category else (fts_match_query, max_results)
            rows = []
            for fts_match_query in search_queries:
                cursor.execute(sql, (fts_match_query, category, category, max_results) if category else (fts_match_query, max_results))
                rows = cursor.fetchall()
                if rows:
                    break

            if not rows:
                return catalog_result or "No highly relevant text matches found in local documents."

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

            document_result = "\n\n---\n\n".join(top_matches)
            if document_result and catalog_result:
                return f"{document_result}\n\n---\n\n{catalog_result}"
            return document_result or catalog_result or "No strong matches found."

    except Exception as e:
        print(f"[SEARCH ERROR]: {e}")
        return "Knowledge search error occurred."


# --- ASYNC LIFESPAN HANDLER (FastAPI startup/shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm
    model_started_at = time.perf_counter()
    print(f"[SYSTEM INFO]: Initializing local assistant with mode='{RUNTIME_CONFIG['mode']}' on Raspberry Pi 5...")
    print(f"[SYSTEM INFO]: Runtime config -> threads={RUNTIME_CONFIG['n_threads']}, batch={RUNTIME_CONFIG['n_batch']}, ctx={RUNTIME_CONFIG['n_ctx']}")

    if not os.path.isfile(MODEL_PATH):
        raise RuntimeError(
            f"Model file not found: {MODEL_PATH}. "
            "Run 'myenv/bin/python utilities/download_model.py' on the Raspberry Pi "
            "or set LOCAL_ASSISTANT_MODEL to an existing GGUF file."
        )

    with silence_all_output():
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=RUNTIME_CONFIG["n_ctx"],
            n_threads=RUNTIME_CONFIG["n_threads"],
            n_batch=RUNTIME_CONFIG["n_batch"],
            flash_attn=RUNTIME_CONFIG["flash_attn"],
            verbose=False,
            loghandler=None
        )
    with METRICS_LOCK:
        METRICS["model_load_ms"] = round((time.perf_counter() - model_started_at) * 1000, 2)

    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        kernel32.SetStdHandle(-11, kernel32.GetStdHandle(-11))
        kernel32.SetStdHandle(-12, kernel32.GetStdHandle(-12))
        sys.stdout = open('CONOUT$', 'w', buffering=1)
        sys.stderr = open('CONOUT$', 'w', buffering=1)

    print("[SYSTEM INFO]: Llama 3.2 engine active and ready.")
    backup_result = create_state_backup()
    print(f"[SYSTEM INFO]: State backup ready ({len(backup_result['created'])} file(s)).")
    memory_store.clear() if not os.path.exists(RUNTIME_CONFIG["memory_db_path"]) else None
    print(f"[SYSTEM INFO]: Local memory store ready at {RUNTIME_CONFIG['memory_db_path']}")

    yield

    print("[SYSTEM INFO]: Shutting down system.")


app = FastAPI(lifespan=lifespan)
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/web_ui", StaticFiles(directory="web_ui"), name="web_ui")


# --- ROUTES ---
@app.get("/", response_class=HTMLResponse)
async def render_browser_interface():
    return HTMLResponse(content=get_chat_html())


@app.get("/api/status")
async def status_endpoint():
    context = read_system_context(SETTINGS)
    return {
        "status": "ready" if llm is not None else "starting",
        "mode": RUNTIME_CONFIG["mode"],
        "effective_mode": RUNTIME_CONFIG["effective_mode"],
        "platform": RUNTIME_CONFIG["platform"],
        "raspberry_pi": RUNTIME_CONFIG["is_raspberry_pi"],
        "safe_execution": RUNTIME_CONFIG["safe_execution"],
        "jellyfin_enabled": bool(JELLYFIN_URL and JELLYFIN_TOKEN),
        "voice_enabled": VOICE_ENABLED,
        "voice_configured": bool(get_voice_transcriber() and get_voice_transcriber().configured),
        "media_directory": str(MEDIA_DIR),
        "threads": RUNTIME_CONFIG["n_threads"],
        "context": RUNTIME_CONFIG["n_ctx"],
        "persona_name": ROBOT_NAME,
        "persona_avatar": PERSONA_AVATAR,
        "system_context": context,
        "metrics": METRICS,
        "port": SERVER_PORT,
    }


@app.get("/api/health")
async def health_endpoint():
    with METRICS_LOCK:
        metrics = dict(METRICS)
    return {
        "status": "ok" if llm is not None else "starting",
        "model_loaded": llm is not None,
        "knowledge_database": os.path.exists(DB_PATH),
        "memory_database": os.path.exists(RUNTIME_CONFIG["memory_db_path"]),
        "conversation_directory": conversation_store.directory.exists(),
        "metrics": metrics,
    }


@app.get("/api/metrics")
async def metrics_endpoint():
    with METRICS_LOCK:
        return dict(METRICS)


@app.get("/api/conversations")
async def conversations_endpoint():
    return {"conversations": conversation_store.list()}


@app.post("/api/conversations")
async def create_conversation_endpoint(request: Request):
    data = await request.json()
    title = data.get("title", "New chat") if isinstance(data, dict) else "New chat"
    return conversation_store.create(title)


@app.get("/api/conversations/{conversation_id}")
async def get_conversation_endpoint(conversation_id: str):
    conversation = conversation_store.get(conversation_id)
    if not conversation:
        return {"status": "error", "message": "Conversation not found."}
    return conversation


@app.patch("/api/conversations/{conversation_id}")
async def rename_conversation_endpoint(conversation_id: str, request: Request):
    data = await request.json()
    title = data.get("title", "") if isinstance(data, dict) else ""
    conversation = conversation_store.rename(conversation_id, title)
    if not conversation:
        raise HTTPException(status_code=400, detail="A non-empty title is required.")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str):
    if not conversation_store.delete(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"status": "ok", "conversation_id": conversation_id}


@app.get("/api/tools")
async def tools_endpoint():
    return {"tools": TOOL_SCHEMAS}


@app.get("/api/voice/status")
async def voice_status_endpoint():
    return {
        "enabled": VOICE_ENABLED,
        "configured": bool(get_voice_transcriber() and get_voice_transcriber().configured),
        "backend": "whisper.cpp",
        "language": voice_transcriber.language,
        "tts_enabled": TTS_ENABLED,
        "tts_configured": bool(get_tts_synthesizer() and get_tts_synthesizer().configured),
        "jellyfin_enabled": JELLYFIN_ENABLED,
    }


@app.post("/api/tts")
async def tts_endpoint(request: Request):
    if not TTS_ENABLED:
        return {"status": "disabled", "message": "Text to speech is disabled in local-ai.config."}
    data = await request.json()
    text = data.get("text", "") if isinstance(data, dict) else ""
    if not voice_operation_lock.acquire(blocking=False):
        return {"status": "busy", "message": "Voice processing is busy. Try again shortly."}
    try:
        synthesizer = get_tts_synthesizer()
        if synthesizer is None:
            return {"status": "disabled", "message": "Text to speech is disabled in local-ai.config."}
        audio = await asyncio.get_running_loop().run_in_executor(None, synthesizer.synthesize, text)
        return StreamingResponse(iter([audio]), media_type="audio/wav", headers={"Cache-Control": "no-store"})
    except Exception as error:
        return {"status": "error", "message": str(error)}
    finally:
        voice_operation_lock.release()


@app.post("/api/voice/transcribe")
async def voice_transcribe_endpoint(request: Request):
    if not VOICE_ENABLED:
        return {"status": "disabled", "message": "Voice input is disabled in local-ai.config."}
    if not voice_operation_lock.acquire(blocking=False):
        return {"status": "busy", "message": "Voice processing is busy. Try again shortly."}
    try:
        transcriber = get_voice_transcriber()
        if transcriber is None:
            return {"status": "disabled", "message": "Voice input is disabled in local-ai.config."}
        audio = await request.body()
        content_type = request.headers.get("content-type", "audio/webm")
        suffix = ".wav" if "wav" in content_type else ".webm"
        text = await asyncio.get_running_loop().run_in_executor(
            None, transcriber.transcribe_bytes, audio, suffix
        )
        if not text.strip():
            return {"status": "empty", "text": "", "message": "No clear speech detected."}
        return {"status": "ok", "text": text}
    except Exception as error:
        return {"status": "error", "message": str(error)}
    finally:
        voice_operation_lock.release()


@app.post("/api/tools/{tool_name}")
async def tool_endpoint(tool_name: str, request: Request):
    data = await request.json()
    return execute_tool(tool_name, data if isinstance(data, dict) else {})


@app.post("/api/backup")
async def backup_endpoint():
    return create_state_backup()


@app.get("/api/proactive")
async def proactive_endpoint():
    if not SETTINGS.get("proactive_mode") or SETTINGS.get("power_saving_mode"):
        return {"message": None, "context": {}}

    context = read_system_context(SETTINGS)
    local_time = context.get("local_time")
    if not local_time:
        return {"message": None, "context": context}

    hour = int(local_time.split(":", 1)[0])
    event_key = f"late-night:{context.get('local_date')}"
    message = None
    if 3 <= hour < 5 and PROACTIVE_STATE["last_key"] != event_key:
        message = f"It is {local_time}. You have entered the suspiciously late hours. Want me to switch to power-saving mode so you can sleep?"
        PROACTIVE_STATE["last_key"] = event_key

    temperature = context.get("cpu_temperature_c")
    thermal_key = f"thermal:{context.get('local_date')}:{hour}"
    if temperature is not None and temperature >= 80 and PROACTIVE_STATE["last_key"] != thermal_key:
        message = f"The Pi is running hot at {temperature:.1f} C. I recommend pausing heavy work and checking airflow."
        PROACTIVE_STATE["last_key"] = thermal_key

    battery = context.get("battery", {}).get("percent")
    battery_key = f"battery:{context.get('local_date')}:{hour}"
    if battery is not None and battery <= 15 and PROACTIVE_STATE["last_key"] != battery_key:
        message = f"Battery is at {battery}%. Please connect power soon."
        PROACTIVE_STATE["last_key"] = battery_key

    return {"message": message, "context": context}


@app.post("/api/robot")
async def robot_endpoint(request: Request):
    data = await request.json()
    conversation_id = data.get("conversation_id")
    conversation = conversation_store.get(conversation_id) if conversation_id else None
    if conversation is None:
        conversation = conversation_store.create()
        conversation_id = conversation["id"]
    persisted_messages = conversation.get("messages", [])
    if persisted_messages:
        data["history"] = [
            (persisted_messages[index]["content"], persisted_messages[index + 1]["content"])
            for index in range(0, len(persisted_messages) - 1, 2)
            if persisted_messages[index].get("role") == "user"
            and persisted_messages[index + 1].get("role") == "assistant"
        ][-3:]
    data["system_context"] = read_system_context(SETTINGS)
    data["power_saving_mode"] = bool(SETTINGS.get("power_saving_mode"))
    data["system_awareness"] = SETTINGS.get("system_awareness", "basic")

    async def event_stream() -> AsyncGenerator[str, None]:
        async with llm_lock:
            loop = asyncio.get_running_loop()
            started_at = time.perf_counter()
            with METRICS_LOCK:
                METRICS["requests"] += 1

            token_queue = queue.Queue()

            def on_token(token: str) -> None:
                token_queue.put(token)

            try:
                request_future = loop.run_in_executor(
                    None,
                    process_robot_request,
                    data,
                    llm,
                    search_database,
                    memory_store,
                    on_token,
                )
                while not request_future.done():
                    while True:
                        try:
                            token = token_queue.get_nowait()
                        except queue.Empty:
                            break
                        yield f"data: {json.dumps({'delta': token})}\n\n"
                    await asyncio.sleep(0.03)
                result_dict, status_code = await request_future
                while True:
                    try:
                        token = token_queue.get_nowait()
                    except queue.Empty:
                        break
                    yield f"data: {json.dumps({'delta': token})}\n\n"
            except Exception:
                with METRICS_LOCK:
                    METRICS["errors"] += 1
                raise

            elapsed_ms = (time.perf_counter() - started_at) * 1000
            response_text = result_dict.get("response", "")
            hardware_cmd = result_dict.get("hardware_cmd", "NONE")
            if hardware_cmd != "NONE":
                action_result = await loop.run_in_executor(
                    None,
                    hw_manager.execute_command,
                    hardware_cmd,
                    data.get("query", ""),
                )
                response_text = action_result
            conversation_store.append(conversation_id, "user", data.get("query", ""))
            conversation = conversation_store.append(conversation_id, "assistant", response_text)
            if conversation:
                memory_store.save_conversation_summary(conversation_id, conversation.get("messages", []))
            with METRICS_LOCK:
                completed = METRICS["completed"] + 1
                METRICS["completed"] = completed
                METRICS["last_latency_ms"] = round(elapsed_ms, 2)
                METRICS["average_latency_ms"] = round(
                    ((METRICS["average_latency_ms"] * (completed - 1)) + elapsed_ms) / completed,
                    2,
                )
                METRICS["last_response_chars"] = len(response_text)

            payload = {
                "response": response_text,
                "hardware_cmd": hardware_cmd,
                "history": result_dict.get("history", []),
                "conversation_id": conversation_id,
                "status": status_code
            }

            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/automation")
async def automation_endpoint(request: Request):
    data = await request.json()
    command = (data.get("command") or "").strip()

    if not command:
        return {"status": "error", "message": "No command supplied."}

    if not is_allowed_command(command):
        return {
            "status": "blocked",
            "message": "This command is not allowed in safe local mode. Use an allowlisted command only."
        }

    try:
        proc = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        response = {
            "status": "ok" if proc.returncode == 0 else "error",
            "code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
        return response
    except FileNotFoundError:
        return {"status": "error", "message": "Command not found on this system."}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Command timed out after 15 seconds."}


if __name__ == "__main__":
    if not is_port_available(SERVER_PORT):
        raise RuntimeError(
            f"Configured port {SERVER_PORT} is already in use. "
            "Stop the other service or change SERVER_PORT in local-ai.config."
        )

    uvicorn.run(app, host="127.0.0.1", port=SERVER_PORT, workers=1)