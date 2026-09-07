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
DATA_DIR = PROJECT_ROOT / "data"
SETTINGS_PATH = Path(os.getenv("LOCAL_ASSISTANT_SETTINGS", str(DATA_DIR / "assistant_settings.json")))
SETTINGS_LOCK = threading.RLock()
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
}


def load_settings() -> Dict[str, Any]:
    with SETTINGS_LOCK:
        settings = dict(DEFAULT_SETTINGS)
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
                stored = json.load(handle)
            if isinstance(stored, dict):
                settings.update({key: value for key, value in stored.items() if key in settings})
        except (OSError, ValueError):
            pass
        settings["proactive_interval_seconds"] = 60
        return settings


def save_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    with SETTINGS_LOCK:
        settings = load_settings()
        for key in DEFAULT_SETTINGS:
            if key in updates:
                settings[key] = updates[key]
        settings["proactive_interval_seconds"] = 60
        temporary_path = SETTINGS_PATH.with_suffix(f"{SETTINGS_PATH.suffix}.tmp")
        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, SETTINGS_PATH)
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
        "memory_db_path": str(DATA_DIR / "local_memory.db"),
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
