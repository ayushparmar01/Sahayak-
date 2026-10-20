"""Bounded retention and cleanup utilities for ephemeral document storage."""
import os
import time
from pathlib import Path

from app.core.config import settings


def cleanup_stale_temp_files(max_age_seconds: int = 3600 * 4) -> int:
    """Scans temp_documents and temp_packages and unlinks files older than max_age_seconds.
    
    Protects kiosk and local filesystem from unbounded storage growth and
    retains files only for the bounded duration of an active user session.
    """
    purged_count = 0
    now = time.time()

    for folder in (settings.DOCUMENTS_TEMP_DIR, settings.PACKAGES_TEMP_DIR):
        if not folder.exists():
            continue
        try:
            for entry in os.scandir(folder):
                if entry.is_file():
                    try:
                        file_age = now - entry.stat().st_mtime
                        if file_age >= max_age_seconds:
                            os.remove(entry.path)
                            purged_count += 1
                    except OSError:
                        pass
        except OSError:
            pass

    return purged_count
