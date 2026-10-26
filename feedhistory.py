#!/usr/bin/env python3
"""Per-module "already posted" store for matterfeed.

Feed modules run in pebble workers under a hard timeout, and a timed-out
worker is killed outright -- no `finally`, no last write. So the history is
never "collect in memory, persist at the end": every post is written through
the moment it is recorded, and nothing after a kill is needed for it to count.

Layout (one shelve file per module, the same file the old list-based history
used):

  post:<sha256>    -> float  time the post was last seen in its feed; dropped
                             after RETENTION_DAYS without being seen
  meta:seeded      -> True   "this module's first run has completed"
  meta:pruned_at   -> float  last retention sweep

A key is a digest of the whole post (channel, text, uploads), attachment bytes
replaced by their own digest, so the store holds ~100 bytes per post rather
than the post itself. The old format kept one pickled list of full posts
(image bytes included) under the module name; that list is not migrated or
even read -- the file is recreated and the module re-seeds as a first run.
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
_SEEDED = 'meta:seeded'
_PRUNED_AT = 'meta:pruned_at'
_PRUNE_INTERVAL = 86400
_REFRESH_INTERVAL = 86400
# Files a dbm backend may keep for one path: sqlite3 (the path, plus -wal/-shm
# after a kill), gdbm (the path), ndbm (.db, or .pag/.dir), dumb (.dat/.dir/.bak).
_DBM_SUFFIXES = ('', '-wal', '-shm', '.db', '.pag', '.dat', '.dir', '.bak')


class BadPost(TypeError):
    """A post whose shape cannot be given an identity (non-JSON value inside).
    A module bug, not a store failure: skip the post, keep the run going."""


def _canonical(value):
    """json.dumps `default` hook: bytes become their digest, never the payload."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {'__bytes_sha256__': hashlib.sha256(bytes(value)).hexdigest()}
    raise TypeError(f'post contains a value of type {type(value).__name__}')


def post_key(post):
    """Stable identity for a post: equal posts map to the same key in any process.

    The whole post counts -- channel, content and uploads -- the same identity
    the original `post not in history[module]` list compare used.
    """
    try:
        canonical = json.dumps(post, sort_keys=True, separators=(',', ':'),
                               ensure_ascii=False, default=_canonical)
    except (TypeError, ValueError) as e:
        raise BadPost(str(e)) from e
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
    `pruned` (keys expired at this open), `prune_error` (sweep failed, str).
    """

    def __init__(self, path, module_name, retention_days=RETENTION_DAYS):
        self._path = path
        self._module_name = module_name
        self._retention = retention_days * 86400
        self.legacy_discarded = False
        self.recovered_from = None
        self.pruned = 0
        self.prune_error = None
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
        db = shelve.open(self._path, flag='c', writeback=False)
        self._backend = dbm.whichdb(self._path)
        return db

    def _open_or_recover(self):
        try:
            return self._open()
        except dbm.error:
            # dbm.error includes OSError, so a lock, a permission problem or
            # a full disk lands here too -- those must propagate, not have a
            # healthy history moved out from under them. Recover only when
            # the file's format is not recognised at all: that is what a kill
            # mid-write under gdbm/ndbm leaves behind, and failing on it every
            # cycle would need an operator to delete the file by hand -- the
            # exact manual fix this module exists to retire.
            if dbm.whichdb(self._path) != '':
                raise
            aside = f'{self._path}.unreadable-{int(time.time())}'
            for file in _dbm_files(self._path):
                os.replace(file, aside + file[len(self._path):])
            self.recovered_from = aside
            return self._open()

    def _first_run_completed(self):
        if self._db.get(_SEEDED) is True:
            return True
        # Anything under the module name is the legacy post list. Membership
        # via keys() so the value -- the file can be hundreds of MB -- is
        # never read. Recreate the file rather than delete the key so the
        # space is freed.
        if self._module_name.encode('utf-8') in self._db.dict.keys():
            self._db.close()
            for file in _dbm_files(self._path):
                os.remove(file)
            self._db = self._open()
            self.legacy_discarded = True
        return False

    # -- per-post --------------------------------------------------------------

    def seen(self, post, refresh=True):
        """Was this post recorded? With `refresh`, also keep it alive: an item
        its feed keeps serving must never expire and be re-announced."""
        key = post_key(post)
        recorded = self._db.get(key)
        if recorded is None:
            return False
        now = time.time()
        if refresh and (now - recorded > _REFRESH_INTERVAL or recorded > now):
            self._db[key] = now
            self._flush()
        return True

    def record(self, post):
        """Mark a post as sent. Durable on return, whether or not close() follows."""
        self._db[post_key(post)] = time.time()
        self._flush()

    def complete_first_run(self):
        """Call once a first-run seed has recorded everything. Until then the
        next open is still a first run, so a kill mid-seed cannot turn the
        unseeded remainder into a flood of 'new' posts."""
        self._db[_SEEDED] = True
        self._flush()

    def _flush(self):
        # sqlite3 autocommits and gdbm/dumb flush on sync(); ndbm buffers in
        # the process and has no sync, so there close is the only flush.
        # whichdb can also come back empty right after a store was created
        # (ndbm writes its file lazily): unknown means take the safe path.
        if self._backend in ('dbm.sqlite3', 'dbm.gnu', 'dbm.dumb'):
            self._db.sync()
        else:
            self._db.close()
            self._db = self._open()

    # -- retention -------------------------------------------------------------

    def _prune(self):
        now = time.time()
        last = self._db.get(_PRUNED_AT)
        # A last sweep in the future means the clock stepped back: sweep now.
        if isinstance(last, (int, float)) and 0 <= now - last < _PRUNE_INTERVAL:
            return
        try:
            cutoff = now - self._retention
            expired = [key for key, recorded in self._db.items()
                       if key.startswith(_KEY_PREFIX)
                       and isinstance(recorded, (int, float)) and recorded < cutoff]
            for key in expired:
                del self._db[key]
            self._db[_PRUNED_AT] = now
            self.pruned = len(expired)
            self._flush()
        except Exception as e:
            # Best effort: a sweep that fails must not stop the module from
            # posting. The caller logs it; it is retried next open.
            self.prune_error = f'{type(e).__name__}: {e}'

    # -- lifecycle -------------------------------------------------------------

    def close(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
