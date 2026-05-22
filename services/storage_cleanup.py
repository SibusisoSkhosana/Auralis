import os
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In-memory throttle timestamp (epoch seconds)
_LAST_CLEANUP_TS = 0
_CLEANUP_THROTTLE_SECONDS = 30 * 60  # 30 minutes

DEFAULT_RETENTION_HOURS = 24
DEFAULT_ENABLED = True

SAFE_AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff'}


def _is_protected(path: Path) -> bool:
    name = path.name
    if name.startswith('.'):
        return True
    if name == '.gitkeep':
        return True
    # protect JSON metadata and DB files
    if path.suffix.lower() in {'.json', '.db', '.sqlite', '.sqlite3'}:
        return True
    # protect config files
    if name.lower().endswith(('config', 'config.json', 'audio_config.json')):
        return True
    return False


def cleanup_directory(path: str, max_age_hours: int):
    """Delete files in `path` older than `max_age_hours`.

    Only removes files with audio extensions and skips protected files.
    Returns number of removed files.
    """
    removed = 0
    try:
        p = Path(path)
        if not p.exists() or not p.is_dir():
            logger.info(f"[CLEANUP] Skipping missing directory: {path}")
            return removed

        cutoff = time.time() - (max_age_hours * 3600)

        for child in p.rglob('*'):
            try:
                if child.is_dir():
                    continue

                if _is_protected(child):
                    continue

                # only consider audio temporary artifacts
                if child.suffix.lower() not in SAFE_AUDIO_EXTENSIONS:
                    continue

                mtime = os.stat(child).st_mtime
                if mtime < cutoff:
                    try:
                        child.unlink()
                        removed += 1
                        logger.info(f"[CLEANUP] Removed old file: {child}")
                    except Exception as e:
                        logger.warning(f"[CLEANUP] Failed to remove {child}: {e}")
            except Exception:
                # ignore file-level errors
                logger.exception(f"[CLEANUP] Error examining file: {child}")

        # Optionally remove empty directories
        for dirpath in sorted([d for d in p.rglob('*') if d.is_dir()], key=lambda x: -len(str(x))):
            try:
                if not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    logger.info(f"[CLEANUP] Removed empty directory: {dirpath}")
            except Exception:
                pass

        return removed
    except Exception as e:
        logger.exception(f"[CLEANUP] Cleanup failed for directory {path}: {e}")
        return removed


def cleanup_old_files():
    """Run cleanup based on environment configuration.

    Reads FILE_RETENTION_HOURS and ENABLE_STORAGE_CLEANUP from env.
    Safe to call repeatedly; catches all exceptions and logs them.
    """
    try:
        enabled = os.getenv('ENABLE_STORAGE_CLEANUP', str(DEFAULT_ENABLED)).lower() in ('1', 'true', 'yes', 'on')
        if not enabled:
            logger.info("[CLEANUP] Storage cleanup disabled by environment")
            return 0

        try:
            retention = int(os.getenv('FILE_RETENTION_HOURS', str(DEFAULT_RETENTION_HOURS)))
        except Exception:
            retention = DEFAULT_RETENTION_HOURS

        removed_total = 0
        for d in ('resources', 'uploads'):
            removed = cleanup_directory(d, retention)
            removed_total += removed

        logger.info(f"[CLEANUP] Cleanup completed, removed {removed_total} files")
        return removed_total
    except Exception:
        logger.exception('[CLEANUP] Unexpected failure during cleanup_old_files')
        return 0


def maybe_cleanup_on_request(throttle_seconds: int = None):
    """Trigger cleanup at most once per throttle window when called from requests.

    Uses an in-memory timestamp to avoid frequent runs.
    """
    global _LAST_CLEANUP_TS
    if throttle_seconds is None:
        throttle_seconds = _CLEANUP_THROTTLE_SECONDS

    try:
        enabled = os.getenv('ENABLE_STORAGE_CLEANUP', str(DEFAULT_ENABLED)).lower() in ('1', 'true', 'yes', 'on')
        if not enabled:
            return 0

        now = time.time()
        if now - _LAST_CLEANUP_TS < throttle_seconds:
            return 0

        _LAST_CLEANUP_TS = now
        return cleanup_old_files()
    except Exception:
        logger.exception('[CLEANUP] Failed to run maybe_cleanup_on_request')
        return 0
