import os
import platform
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
        "memory_db_path": "local_memory.db",
        "automation_allowlist": list(DEFAULT_ALLOWLIST),
        "safe_execution": True,
    }

    if normalized_mode == "low_ram":
        base.update({
            "n_threads": 2,
            "n_batch": 128,
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

    return base
