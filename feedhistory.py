#!/usr/bin/env python3
"""Per-module "already posted" store for matterfeed.

matterfeed runs every feed module in a pebble worker with a hard timeout, and
pebble terminates a timed-out worker outright: nothing after the kill runs, not
even `finally`. The history therefore cannot be "collect in memory, persist at
the end": a worker killed after its first post but before that final write
re-sends the same items on every cycle until someone deletes the cache.

So a post is written through to disk the moment it is recorded, one key per
post, independent of close(). Keys are a digest of the post (channel, text,
uploads), so the store holds a few dozen bytes per post rather than the post
itself -- attachment bytes included -- and neither the lookup nor the write
grows with the size of the history. Each key holds the time it was recorded,
and keys older than RETENTION_DAYS are dropped on open, so the store is
bounded by the feeds' rate, not by the bot's uptime.

Storage is the same `shelve` file the original list-based history used, so an
existing cache is picked up in place. The legacy shape (one pickled list under
the module name) is migrated on first open: every post in it becomes a key, so
an upgrade never re-posts the backlog. The module-name key is kept, holding
`True`, as the "this module has run before" marker that drives first_run.

Only the bot's own process ever writes this file, so unpickling it is
unpickling our own data; shelve is kept for in-place compatibility with the
caches already on operators' disks.

Stdlib-only, like feedutils, so it is testable under the dependency-free CI
runner.
"""

import hashlib
import json
import shelve
import time

# How long a post stays "seen". Dedup only has to remember an item for as long
# as it can still appear in its feed; after that the key is dead weight. Every
# feed here serves at most its latest ENTRIES items, so 90 days is generous.
# The cost of being wrong is one re-post of an item a feed re-bumps after that
# long, not a loop.
RETENTION_DAYS = 90

_KEY_PREFIX = 'post:'


def _canonical(value):
    """json.dumps `default` hook: bytes become their digest, never the payload."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {'__bytes_sha256__': hashlib.sha256(bytes(value)).hexdigest()}
    raise TypeError(f'post contains an unhashable value of type {type(value).__name__}')


def post_key(post):
    """Stable identity for a post: equal posts map to the same key in any process.

    The whole post counts -- channel, content and uploads -- which is the same
    identity the original `post not in history[module]` list compare used, so
    migrating from that history changes nothing about what is considered seen.
    """
    canonical = json.dumps(post, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=False, default=_canonical)
    return _KEY_PREFIX + hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class PostHistory:
    def __init__(self, path, module_name, retention_days=RETENTION_DAYS):
        self._path = path
        self._module_name = module_name
        self._retention = retention_days * 86400
        self._db = self._open()
        marker = self._db.get(module_name)
        self.first_run = marker is None
        if isinstance(marker, list):
            self._migrate(marker)
        elif self.first_run:
            self._db[module_name] = True
            self._flush()
        else:
            self._prune()

    def _prune(self):
        # Runs once per open (once per module per cycle). The store is a few
        # hundred bytes per post, so even a year's worth is a quick scan.
        cutoff = time.time() - self._retention
        # Materialise the key list first: _recorded_at may write to the store.
        expired = [key for key in list(self._db.keys())
                   if key.startswith(_KEY_PREFIX) and self._recorded_at(key) < cutoff]
        if expired:
            for key in expired:
                del self._db[key]
            self._flush()

    def _recorded_at(self, key):
        value = self._db.get(key)
        # Any value that is not a timestamp is from a store written before
        # retention existed; count it as recorded now so it ages out from here.
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        self._db[key] = time.time()
        return self._db[key]

    def _open(self):
        # No writeback: with it, shelve buffers every mutation in memory and
        # only writes on sync()/close() -- exactly the all-or-nothing final
        # write that a timeout kill turns into a repost loop.
        return shelve.open(self._path, flag='c', writeback=False)

    def _flush(self):
        # Which dbm backs the file depends on the interpreter (sqlite3 on
        # 3.13+, gdbm/ndbm/dumb before), and only some of them push a write to
        # disk on sync(): ndbm buffers in the process and has no sync at all,
        # so a killed worker loses everything since open(). Closing is the one
        # operation every backend flushes on, and we write at most a handful
        # of posts per run, so close-and-reopen is cheap and backend-proof.
        self._db.close()
        self._db = self._open()

    def _migrate(self, legacy_posts):
        # Legacy entries carry no date; they start their retention clock now.
        now = time.time()
        for post in legacy_posts:
            try:
                self._db[post_key(post)] = now
            except TypeError:
                # A legacy entry we cannot derive a key for would, at worst, be
                # posted once more; it must not block the migration.
                continue
        self._db[self._module_name] = True
        self._flush()

    def seen(self, post):
        return post_key(post) in self._db

    def record(self, post):
        """Mark a post as sent. Durable on return, whether or not close() follows."""
        self._db[post_key(post)] = time.time()
        self._flush()

    def close(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
