import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import config, db, drive, faces

log = logging.getLogger("identipix.indexer")
_sem = threading.Semaphore(config.MAX_CONCURRENT_EVENTS)
_active: set[str] = set()
_lock = threading.Lock()


def start_index(event_id: str) -> bool:
    """Start a background index/sync. No-op (False) if one is already running."""
    with _lock:
        if event_id in _active:
            return False
        _active.add(event_id)
    threading.Thread(target=_run, args=(event_id,), daemon=True).start()
    return True


def _process(event_id: str, f: dict) -> None:
    embs = []
    try:
        img = drive.fetch_image(f)
        embs = [faces.embed(img, row) for row in faces.detect(img)]
    except Exception as e:  # one bad file must not fail the event
        log.warning("file %s failed: %s", f.get("id"), e)
    db.record_photo(event_id, f["id"], f.get("name", ""), embs)


def _run(event_id: str) -> None:
    try:
        with _sem:
            ev = db.get_event(event_id)
            if ev is None:
                return
            try:
                images = drive.list_images(ev["folder_id"])
            except Exception as e:
                log.error("listing failed for %s: %s", event_id, e)
                db.update_event(event_id, status="error", error=str(e))
                return
            if len(images) > config.MAX_PHOTOS:
                msg = f"This folder has {len(images)} photos. The limit is {config.MAX_PHOTOS}. Split it into smaller folders."
                db.update_event(event_id, status="error", error=msg)
                return
            known = db.processed_file_ids(event_id)
            todo = [f for f in images if f["id"] not in known]
            db.update_event(event_id, total=len(images), done=len(images) - len(todo), status="indexing", error=None)
            with ThreadPoolExecutor(config.INDEX_WORKERS) as pool:
                list(pool.map(lambda f: _process(event_id, f), todo))
            db.update_event(event_id, status="ready", last_sync=int(time.time()))
    except Exception as e:
        log.exception("index crashed for %s", event_id)
        db.update_event(event_id, status="error", error=str(e))
    finally:
        with _lock:
            _active.discard(event_id)


def resume_all() -> None:
    for eid in db.indexing_event_ids():
        start_index(eid)


def maybe_sync(ev) -> None:
    if ev["status"] == "ready" and time.time() - (ev["last_sync"] or 0) > config.SYNC_INTERVAL_MIN * 60:
        db.update_event(ev["id"], status="indexing")
        start_index(ev["id"])


def expire_old(matcher: faces.Matcher) -> None:
    for eid in db.expired_event_ids(int(time.time()) - config.RETENTION_DAYS * 86400):
        db.delete_event(eid)
        matcher.forget(eid)
