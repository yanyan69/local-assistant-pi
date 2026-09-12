import os
import platform
import json
import threading
from pathlib import Path
from typing import Dict, Any, List


DEFAULT_ALLOWLIST: List[str] = [
    "ls",
    "ls -la",
    "pwd",
    "whoami",
    "uname -a",
    "python --version",
    "python -V",
    "git --version",
    "git status",
    "git log -n 5",
    "python -m http.server 8000",
    "python -m http.server 8080",
]

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_project_local_ai_config_path() -> Path:
    """Return the canonical local-ai.config that the server and UI should edit."""
    return PROJECT_ROOT / "local-ai.config"


def _config_candidates() -> List[Path]:
    candidates = []
    explicit = os.getenv("LOCAL_ASSISTANT_CONFIG")
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.name == "nt":
        candidates.append(Path(os.getenv("APPDATA", str(Path.home()))) / "local-assistant" / "local-ai.config")
    else:
        candidates.append(Path.home() / ".config" / "local-assistant" / "local-ai.config")
    candidates.append(Path.home() / ".local-ai.config")
    candidates.append(PROJECT_ROOT / "local-ai.config")
    return candidates


def _read_config_file() -> Dict[str, str]:
    for path in _config_candidates():
        try:
            with path.open("r", encoding="utf-8") as handle:
                values = {}
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    value = value.strip().strip('"').strip("'")
                    values[key.strip().upper()] = os.path.expandvars(os.path.expanduser(value))
                return values
        except OSError:
            continue
    return {}


FILE_CONFIG = _read_config_file()


def config_value(key: str, default: Any = None, env_names: List[str] | None = None) -> Any:
    """Return an environment override, then local-ai.config value, then default."""
    for env_name in env_names or [key]:
        if os.getenv(env_name) is not None:
            return os.getenv(env_name)
    return FILE_CONFIG.get(key.upper(), default)


def config_path(key: str, default: Path, env_names: List[str] | None = None) -> Path:
    value = Path(str(config_value(key, str(default), env_names)))
    return value if value.is_absolute() else PROJECT_ROOT / value


DATA_DIR = config_path("DATA_DIR", PROJECT_ROOT / "data", ["LOCAL_ASSISTANT_DATA_DIR"])
KNOWLEDGE_BASE_DIR = config_path("KNOWLEDGE_BASE_DIR", PROJECT_ROOT / "knowledge_base", ["LOCAL_ASSISTANT_KNOWLEDGE_BASE_DIR"])
BUILD_DIR = config_path("BUILD_DIR", PROJECT_ROOT / "build_tmp", ["LOCAL_ASSISTANT_BUILD_DIR"])
MEDIA_DIR = config_path("MEDIA_DIR", PROJECT_ROOT / "assets" / "music", ["LOCAL_MEDIA_DIR", "LOCAL_MUSIC_DIR"])
CONVERSATIONS_DIR = config_path("CONVERSATIONS_DIR", DATA_DIR / "conversations", ["LOCAL_ASSISTANT_CONVERSATIONS_DIR"])
SETTINGS_PATH = config_path("SETTINGS_PATH", DATA_DIR / "assistant_settings.json", ["LOCAL_ASSISTANT_SETTINGS"])
MEMORY_DB_PATH = config_path("MEMORY_DB_PATH", DATA_DIR / "local_memory.db", ["LOCAL_ASSISTANT_MEMORY_DB"])
KNOWLEDGE_DB_PATH = config_path("KNOWLEDGE_DB_PATH", DATA_DIR / "knowledge_base.db", ["LOCAL_ASSISTANT_KNOWLEDGE_DB"])
MODEL_PATH = config_path("MODEL_PATH", DATA_DIR / "Llama-3.2-1B-Instruct.Q4_K_M.gguf", ["LOCAL_ASSISTANT_MODEL"])
JELLYFIN_URL = str(config_value("JELLYFIN_URL", "", ["JELLYFIN_URL"]))
JELLYFIN_TOKEN = str(config_value("JELLYFIN_TOKEN", "", ["JELLYFIN_TOKEN"]))
JELLYFIN_ENABLED = str(config_value("JELLYFIN_ENABLED", "false", ["LOCAL_ASSISTANT_JELLYFIN_ENABLED"])).strip().lower() in {"1", "true", "yes", "on"}
SERVER_PORT = int(config_value("SERVER_PORT", os.getenv("PORT", "5000"), ["LOCAL_ASSISTANT_PORT", "PORT"]))
PERSONA_MODULE = str(config_value("PERSONA_MODULE", "persona.reze_persona", ["LOCAL_ASSISTANT_PERSONA_MODULE"]))
VOICE_ENABLED = str(config_value("VOICE_ENABLED", "false", ["LOCAL_ASSISTANT_VOICE_ENABLED"])).strip().lower() in {"1", "true", "yes", "on"}
WHISPER_CPP_PATH = str(config_value("WHISPER_CPP_PATH", "whisper-cli", ["LOCAL_ASSISTANT_WHISPER_CPP_PATH"]))
WHISPER_MODEL_PATH = config_path("WHISPER_MODEL_PATH", DATA_DIR / "ggml-base.en.bin", ["LOCAL_ASSISTANT_WHISPER_MODEL"])
VOICE_LANGUAGE = str(config_value("VOICE_LANGUAGE", "en", ["LOCAL_ASSISTANT_VOICE_LANGUAGE"]))
FFMPEG_PATH = str(config_value("FFMPEG_PATH", "ffmpeg", ["LOCAL_ASSISTANT_FFMPEG_PATH"]))
WHISPER_NO_SPEECH_THRESHOLD = str(config_value("WHISPER_NO_SPEECH_THRESHOLD", "0.7", ["LOCAL_ASSISTANT_WHISPER_NO_SPEECH_THRESHOLD"]))
TTS_ENABLED = str(config_value("TTS_ENABLED", "false", ["LOCAL_ASSISTANT_TTS_ENABLED"])).strip().lower() in {"1", "true", "yes", "on"}
PIPER_PATH = str(config_value("PIPER_PATH", "piper", ["LOCAL_ASSISTANT_PIPER_PATH"]))
TTS_MODEL_PATH = config_path("TTS_MODEL_PATH", PROJECT_ROOT / "assets" / "voices" / "en_US-lessac-medium.onnx", ["LOCAL_ASSISTANT_TTS_MODEL"])
TTS_VOICE_DIR = config_path("TTS_VOICE_DIR", PROJECT_ROOT / "assets" / "voices", ["LOCAL_ASSISTANT_TTS_VOICE_DIR"])
TTS_LENGTH_SCALE = str(config_value("TTS_LENGTH_SCALE", "1.0", ["LOCAL_ASSISTANT_TTS_LENGTH_SCALE"]))
SETTINGS_LOCK = threading.RLock()
_LEGACY_SETTINGS_OVERRIDES: Dict[str, Any] = {}
DEFAULT_SETTINGS: Dict[str, Any] = {
    "system_awareness": "basic",
    "power_saving_mode": False,
    "proactive_mode": False,
    "allow_clock": True,
    "allow_thermal_status": True,
    "allow_battery_status": True,
    "allow_process_inspection": False,
    "proactive_interval_seconds": 60,
    "max_memory_summary_chars": 900,
    "jellyfin_enabled": JELLYFIN_ENABLED and bool(JELLYFIN_URL and JELLYFIN_TOKEN),
}


def load_settings() -> Dict[str, Any]:
    """Load runtime settings from local-ai.config and environment overrides."""
    with SETTINGS_LOCK:
        settings = dict(DEFAULT_SETTINGS)
        boolean_keys = {
            "power_saving_mode", "proactive_mode", "allow_clock",
            "allow_thermal_status", "allow_battery_status", "allow_process_inspection",
        }
        for key in boolean_keys:
            value = config_value(key.upper(), settings[key], [key.upper(), f"LOCAL_ASSISTANT_{key.upper()}"])
            if isinstance(value, str):
                value = value.strip().lower() in {"1", "true", "yes", "on"}
            settings[key] = bool(value)
        settings["system_awareness"] = str(config_value("SYSTEM_AWARENESS", settings["system_awareness"], ["SYSTEM_AWARENESS"]))
        settings["max_memory_summary_chars"] = int(config_value("MAX_MEMORY_SUMMARY_CHARS", settings["max_memory_summary_chars"], ["MAX_MEMORY_SUMMARY_CHARS"]))
        settings.update(_LEGACY_SETTINGS_OVERRIDES)
        settings["proactive_interval_seconds"] = 60
        settings["jellyfin_enabled"] = bool(JELLYFIN_URL and JELLYFIN_TOKEN)
        return settings


def save_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy compatibility for callers; configuration is now edited in local-ai.config."""
    with SETTINGS_LOCK:
        settings = load_settings()
        for key in DEFAULT_SETTINGS:
            if key in updates:
                settings[key] = updates[key]
        settings["proactive_interval_seconds"] = 60
        _LEGACY_SETTINGS_OVERRIDES.update({key: settings[key] for key in DEFAULT_SETTINGS if key in updates})
        return settings


def build_runtime_config(mode: str = "balanced") -> Dict[str, Any]:
    """Build a Pi-friendly runtime configuration used for stability and local automation."""
    normalized_mode = (mode or "balanced").lower()
    cpu_count = os.cpu_count() or 4
    thread_count = max(1, min(4, cpu_count))

    base = {
        "mode": normalized_mode,
        "platform": platform.platform(),
        "is_raspberry_pi": "raspberry" in platform.platform().lower(),
        "n_threads": thread_count,
        "n_batch": 256,
        "n_ctx": 2048,
        "flash_attn": True,
        "memory_db_path": str(MEMORY_DB_PATH),
        "automation_allowlist": list(DEFAULT_ALLOWLIST),
        "safe_execution": True,
        "settings": load_settings(),
    }

    if normalized_mode == "low_ram":
        base.update({
            "n_threads": 2,
            "n_batch": 64,
            "n_ctx": 1024,
            "flash_attn": True,
        })
    elif normalized_mode == "high_quality":
        base.update({
            "n_threads": min(4, max(2, cpu_count)),
            "n_batch": 512,
            "n_ctx": 4096,
            "flash_attn": True,
        })
    elif normalized_mode == "balanced":
        base.update({
            "n_threads": max(2, min(4, cpu_count)),
            "n_batch": 256,
            "n_ctx": 2048,
            "flash_attn": True,
        })

    if base["settings"].get("power_saving_mode"):
        base.update({
            "effective_mode": "power_saving",
            "n_threads": min(2, max(1, cpu_count)),
            "n_batch": 64,
            "n_ctx": 1024,
        })
    else:
        base["effective_mode"] = normalized_mode

    return base
