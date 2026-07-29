"""One-shot bootstrap: create folders, DB, logging, health check."""
from __future__ import annotations

from . import migrations
from .config import all_dirs
from .logging_config import setup as setup_logging, get_logger
from .utils import safe_disk_free
from .config import TEMP_DIR


def run() -> dict:
    for d in all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    log = setup_logging()
    version = migrations.apply()
    free = safe_disk_free(TEMP_DIR)
    log.info("bootstrap ok schema=%s free=%s", version, free)
    return {
        "schema_version": version,
        "dirs": [str(d) for d in all_dirs()],
        "free_bytes": free,
    }
