#!/usr/bin/env python3
"""Per-module "already posted" store for matterfeed.

Feed modules run in pebble workers under a hard timeout, and a timed-out
worker is killed outright -- no `finally`, no last write. So the history is
never "collect in memory, persist at the end": every post is written through
the moment it is recorded, and nothing after a kill is needed for it to count.

Layout (one shelve file per module, the same file the old list-based history
used):

  post:<sha256>   -> float   time the post was recorded; refreshed when the
                             post is seen again, dropped after RETENTION_DAYS
  <module_name>   -> True    "this module's first run has completed"
  pruned_at       -> float   last retention sweep

A key is a digest of the whole post (channel, text, uploads), attachment bytes
replaced by their own digest, so the store holds ~100 bytes per post rather
than the post itself. The old format kept one pickled list of full posts
(image bytes included) under the module name; that list is not migrated, it
is discarded without being unpickled and the module re-seeds as a first run.
A first run records what the feed currently serves and posts nothing, so the
upgrade re-posts nothing either.

Only the bot's own process writes this file, so unpickling it is unpickling
our own data; shelve stays so existing caches are reused in place.

Stdlib-only, like feedutils, so it is testable under the dependency-free CI
runner.
"""

import dbm
import hashlib
import json
import os
import shelve
import time

# How long a post stays "seen" after it was last observed in its feed. Expiry
# therefore means "absent from the feed for this long", not "first posted this
# long ago": a feed that keeps serving an item keeps it seen indefinitely.
RETENTION_DAYS = 90

_KEY_PREFIX = 'post:'
_PRUNED_AT = 'pruned_at'
_PRUNE_INTERVAL = 86400
_REFRESH_INTERVAL = 86400
# A pickled True/False/float is a handful of bytes; anything bigger under the
# module-name key is the legacy post list, which we never want to load.
_MARKER_MAX_BYTES = 64
# Files a dbm backend may create for one path (sqlite/gdbm: the path itself;
# ndbm: .db; dumb: .dat/.dir/.bak).
_DBM_SUFFIXES = ('', '.db', '.dat', '.dir', '.bak')


def _canonical(value):
    """json.dumps `default` hook: bytes become their digest, never the payload."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {'__bytes_sha256__': hashlib.sha256(bytes(value)).hexdigest()}
    raise TypeError(f'post contains an unhashable value of type {type(value).__name__}')


def post_key(post):
    """Stable identity for a post: equal posts map to the same key in any process.

    The whole post counts -- channel, content and uploads -- the same identity
    the original `post not in history[module]` list compare used.
    """
    canonical = json.dumps(post, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=False, default=_canonical)
    # surrogatepass: feed JSON can carry a lone surrogate (a truncated emoji);
    # the key must still be derivable, or that one item stops the whole run.
    return _KEY_PREFIX + hashlib.sha256(canonical.encode('utf-8', 'surrogatepass')).hexdigest()


def _dbm_files(path):
    return [path + suffix for suffix in _DBM_SUFFIXES if os.path.exists(path + suffix)]


class PostHistory:
    """Open with `first_run`; call `seen`/`record` per post; `complete_first_run`
    once a first-run seed finished; `close` in a finally.

    Attributes for the caller's log line: `first_run`, `legacy_discarded`,
    `recovered_from` (path the unreadable store was moved to, or None),
    `pruned` (keys expired at this open).
    """

    def __init__(self, path, module_name, retention_days=RETENTION_DAYS):
        self._path = path
        self._module_name = module_name
        self._retention = retention_days * 86400
        self.legacy_discarded = False
        self.recovered_from = None
        self.pruned = 0
        self._db = self._open_or_recover()
        try:
            self.first_run = not self._first_run_completed()
            if not self.first_run:
                self._prune()
        except Exception:
            self._db.close()
            raise

    # -- opening ---------------------------------------------------------------

    def _open(self):
        # Never writeback: it buffers every mutation in memory until close(),
        # which is exactly the all-or-nothing write a kill turns into a loop.
        return shelve.open(self._path, flag='c', writeback=False)

    def _open_or_recover(self):
        try:
            return self._open()
        except dbm.error:
            # A kill mid-write can leave a gdbm/ndbm file unreadable. Failing
            # here every cycle would need an operator to delete the file by
            # hand -- the exact manual fix this module exists to retire. Move
            # it aside (kept for forensics) and start fresh: a first run.
            aside = f'{self._path}.unreadable-{int(time.time())}'
            for file in _dbm_files(self._path):
                os.replace(file, aside + file[len(self._path):])
            self.recovered_from = aside
            return self._open()

    def _first_run_completed(self):
        raw = self._db.dict.get(self._module_name.encode('utf-8'))
        if raw is None:
            return False
        if len(raw) <= _MARKER_MAX_BYTES and self._db.get(self._module_name) is True:
            return True
        # Legacy post list (or an empty one, or anything else): the file can
        # be hundreds of MB and the list is never needed -- see module doc.
        # Recreate the file rather than delete the key so the space is freed.
        self._db.close()
        for file in _dbm_files(self._path):
            os.remove(file)
        self._db = self._open()
        self.legacy_discarded = True
        return False

    # -- per-post --------------------------------------------------------------

    def seen(self, post):
        key = post_key(post)
        recorded = self._db.get(key)
        if recorded is None:
            return False
        # Keep an item alive while its feed keeps serving it. No flush: losing
        # a refresh to a kill costs nothing, close() persists it otherwise.
        now = time.time()
        if now - recorded > _REFRESH_INTERVAL:
            self._db[key] = now
        return True

    def record(self, post):
        """Mark a post as sent. Durable on return, whether or not close() follows."""
        self._db[post_key(post)] = time.time()
        self._flush()

    def complete_first_run(self):
        """Call once a first-run seed has recorded everything. Until then the
        next open is still a first run, so a kill mid-seed cannot turn the
        unseeded remainder into a flood of 'new' posts."""
        self._db[self._module_name] = True
        self._flush()

    def _flush(self):
        # Which dbm backs the file depends on the interpreter (sqlite3 on
        # 3.13+, gdbm/ndbm/dumb before) and only some flush on sync(): ndbm
        # buffers in-process and has none. Close is the one flush every
        # backend honours, and a run writes a handful of posts.
        self._db.close()
        self._db = self._open()

    # -- retention -------------------------------------------------------------

    def _prune(self):
        now = time.time()
        last = self._db.get(_PRUNED_AT)
        if isinstance(last, (int, float)) and now - last < _PRUNE_INTERVAL:
            return
        cutoff = now - self._retention
        expired = [key for key, recorded in self._db.items()
                   if key.startswith(_KEY_PREFIX)
                   and isinstance(recorded, (int, float)) and recorded < cutoff]
        for key in expired:
            del self._db[key]
        self._db[_PRUNED_AT] = now
        self.pruned = len(expired)
        self._flush()

    # -- lifecycle -------------------------------------------------------------

    def close(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
