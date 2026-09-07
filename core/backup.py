"""Small local backups for assistant state."""

import shutil
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BACKUP_DIR = DATA_DIR / "backups"


def create_state_backup() -> dict:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    copied = []
    for filename in ("local_memory.db", "assistant_settings.json"):
        source = DATA_DIR / filename
        if source.exists():
            destination = BACKUP_DIR / f"{stamp}-{filename}"
            shutil.copy2(source, destination)
            copied.append(str(destination.relative_to(PROJECT_ROOT)))

    backups = sorted(BACKUP_DIR.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True)
    for old_backup in backups[6:]:
        old_backup.unlink(missing_ok=True)

    return {"status": "ok", "created": copied, "retained": min(len(backups), 6)}
