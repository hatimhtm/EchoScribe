"""Watch a directory and process audio files as they land.

Pair it with Zoom / Loom / Teams local-recording folders and the script
will pick up new files, run the full pipeline, and write the brief next to
them. Install with the `[watch]` extra:

    pip install 'echoscribe[watch]'
    echoscribe watch ./recordings --post-slack
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".mp4", ".m4a", ".wav", ".webm", ".mpeg", ".mpga"}


def _is_audio(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS


def _wait_until_stable(path: Path, settle_seconds: float = 2.0) -> bool:
    """Wait for a file to stop growing (i.e. the recorder finished writing).
    Returns True once size is stable, False if the file disappears."""
    try:
        last = path.stat().st_size
    except FileNotFoundError:
        return False

    while True:
        time.sleep(settle_seconds)
        try:
            current = path.stat().st_size
        except FileNotFoundError:
            return False
        if current == last:
            return True
        last = current


def watch_directory(directory: Path, on_new_file: Callable[[Path], None]) -> None:
    """Block forever, calling `on_new_file` for each new audio file that
    arrives in `directory`. Files already present at start are skipped.

    Uses watchdog if available; falls back to polling for environments
    where filesystem events don't work (network mounts, Docker bind mounts).
    """
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)

    seen: set[Path] = {p for p in directory.iterdir() if _is_audio(p)}
    logger.info("watching %s (%d files already present, skipped)", directory, len(seen))

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        logger.info("watchdog not installed — using poll fallback (2s)")
        _poll_loop(directory, seen, on_new_file)
        return

    lock = threading.Lock()

    class Handler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            path = Path(event.src_path)
            if not _is_audio(path):
                return
            with lock:
                if path in seen:
                    return
                seen.add(path)
            threading.Thread(
                target=_process_when_stable,
                args=(path, on_new_file),
                daemon=True,
            ).start()

    observer = Observer()
    observer.schedule(Handler(), str(directory), recursive=False)
    observer.start()
    try:
        while observer.is_alive():
            observer.join(1.0)
    except KeyboardInterrupt:
        logger.info("stopping watcher")
        observer.stop()
        observer.join()


def _poll_loop(
    directory: Path,
    seen: set[Path],
    on_new_file: Callable[[Path], None],
    interval: float = 2.0,
) -> None:
    while True:
        try:
            current = {p for p in directory.iterdir() if _is_audio(p)}
        except FileNotFoundError:
            time.sleep(interval)
            continue

        for path in current - seen:
            seen.add(path)
            threading.Thread(
                target=_process_when_stable,
                args=(path, on_new_file),
                daemon=True,
            ).start()
        time.sleep(interval)


def _process_when_stable(path: Path, on_new_file: Callable[[Path], None]) -> None:
    if not _wait_until_stable(path):
        return
    logger.info("processing %s", path.name)
    try:
        on_new_file(path)
    except Exception:
        logger.exception("processing failed for %s", path)
