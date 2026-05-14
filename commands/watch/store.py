#!/usr/bin/env python3
"""Persistent per-user keyword watch store.

Loaded both by `commands/watch/command.py` (user-facing CLI) and by the
matterbot.py scan hook (notification path). All mutations go through a
single threading.RLock because mattermost dispatches command modules in a
ThreadPoolExecutor while the scan hook also runs in the same executor —
two threads can race on the same shelf otherwise.

Storage shape (JSON-on-disk):

  {
    "<mattermost_userid>": {
      "<keyword_lower>": <expiry_unix_ts_int> | null,
      ...
    },
    ...
  }
"""

import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path

log = logging.getLogger("MatterBot")

_STATE_FILE = Path(__file__).parent / "watchlist.json"
_LOCK = threading.RLock()
_DATA: dict | None = None


def _load() -> dict:
    global _DATA
    if _DATA is not None:
        return _DATA
    if not _STATE_FILE.is_file():
        _DATA = {}
        return _DATA
    try:
        with _STATE_FILE.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        log.exception("watch: could not load %s; starting with empty store", _STATE_FILE)
        _DATA = {}
        return _DATA
    if not isinstance(raw, dict):
        log.warning("watch: %s root is not an object; resetting", _STATE_FILE)
        _DATA = {}
        return _DATA
    # Lightly validate the schema so a hand-edited file with garbage doesn't
    # break the whole store. Unknown shapes are dropped, not crashed on.
    cleaned: dict = {}
    for userid, watches in raw.items():
        if not isinstance(userid, str) or not isinstance(watches, dict):
            continue
        kept: dict = {}
        for kw, expiry in watches.items():
            if not isinstance(kw, str):
                continue
            if expiry is not None and not isinstance(expiry, int):
                continue
            kept[kw] = expiry
        if kept:
            cleaned[userid] = kept
    _DATA = cleaned
    return _DATA


def _persist_locked() -> None:
    """Caller must hold _LOCK."""
    data = _load()
    # Atomic write so a crash mid-flush doesn't leave a half-written file.
    fd, tmp_path = tempfile.mkstemp(
        prefix="watchlist-", suffix=".json", dir=str(_STATE_FILE.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(tmp_path, _STATE_FILE)
    except Exception:
        log.exception("watch: failed to persist watchlist")
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _sweep_user_locked(userid: str, now: int) -> None:
    """Caller must hold _LOCK. Drops expired watches for one user."""
    data = _load()
    watches = data.get(userid)
    if not watches:
        return
    expired = [kw for kw, exp in watches.items() if exp is not None and exp <= now]
    for kw in expired:
        del watches[kw]
    if not watches:
        del data[userid]


def list_for_user(userid: str) -> list[tuple[str, int | None]]:
    """Return [(keyword, expiry_ts_or_None), ...] sorted by keyword."""
    now = int(time.time())
    with _LOCK:
        _sweep_user_locked(userid, now)
        watches = _load().get(userid, {})
        return sorted(watches.items())


def add(userid: str, keyword: str, expiry_ts: int | None, max_per_user: int) -> tuple[bool, str]:
    """Return (success, reason). Caller has already validated keyword shape."""
    keyword = keyword.lower()
    now = int(time.time())
    with _LOCK:
        data = _load()
        _sweep_user_locked(userid, now)
        watches = data.setdefault(userid, {})
        is_replace = keyword in watches
        if not is_replace and len(watches) >= max_per_user:
            return False, f"limit of {max_per_user} watches per user reached"
        watches[keyword] = expiry_ts
        try:
            _persist_locked()
        except Exception as e:
            # Roll back the in-memory mutation so reload doesn't silently
            # show a watch that didn't actually persist.
            if is_replace:
                # We don't have the prior value handy; this is rare enough
                # that "user re-adds" is an acceptable degradation.
                pass
            else:
                del watches[keyword]
            return False, f"persistence failed: {e}"
    return True, "replaced" if is_replace else "added"


def delete(userid: str, keyword: str) -> bool:
    keyword = keyword.lower()
    with _LOCK:
        data = _load()
        watches = data.get(userid)
        if not watches or keyword not in watches:
            return False
        del watches[keyword]
        if not watches:
            del data[userid]
        try:
            _persist_locked()
        except Exception:
            return False
    return True


def clear(userid: str) -> int:
    with _LOCK:
        data = _load()
        watches = data.pop(userid, None)
        count = len(watches) if watches else 0
        if count:
            try:
                _persist_locked()
            except Exception:
                # Best-effort: in-memory state is now divergent from disk, but
                # the next successful mutation will reconverge.
                pass
    return count


def iter_active() -> list[tuple[str, str]]:
    """Return a flat list of (userid, keyword) for all non-expired watches.

    Snapshot copy — safe to iterate without holding the lock.
    """
    now = int(time.time())
    out: list[tuple[str, str]] = []
    with _LOCK:
        data = _load()
        for userid, watches in list(data.items()):
            for kw, exp in list(watches.items()):
                if exp is None or exp > now:
                    out.append((userid, kw))
    return out
