"""Local disk management: preflight, temp path, orphan quarantine, cleanup."""
from __future__ import annotations

import shutil
from pathlib import Path

from .config import TEMP_DIR
from .logging_config import get_logger
from .utils import safe_disk_free

_log = get_logger("teledrive.storage")

RESERVE_BYTES = 200 * 1024 * 1024  # keep 200 MB headroom
QUARANTINE = TEMP_DIR / "_quarantine"


def preflight(required_bytes: int) -> tuple[bool, int]:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    free = safe_disk_free(TEMP_DIR)
    return (free >= required_bytes + RESERVE_BYTES, free)


def temp_path_for(item_id: str, safe_name: str) -> Path:
    d = TEMP_DIR / item_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe_name}.part"


def cleanup_item(item_id: str) -> None:
    d = TEMP_DIR / item_id
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def quarantine_orphans(known_item_ids: set[str]) -> list[str]:
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    if not TEMP_DIR.exists():
        return moved
    for entry in TEMP_DIR.iterdir():
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        if entry.name not in known_item_ids:
            target = QUARANTINE / entry.name
            try:
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)
                shutil.move(str(entry), str(target))
                moved.append(entry.name)
            except Exception as e:
                _log.warning("quarantine move failed for %s: %s", entry, e)
    return moved
