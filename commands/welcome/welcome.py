#!/usr/bin/env python3

"""Shared welcome-module helpers.

Owns:
  - SQLite schema for welcome_configs / welcomed_users / channel_admins
  - The on_join() event handler called by matterbot.py from two event paths
    (system_join_channel posts and user_added events) and from the
    post-reconnect reconcile pass
  - is_welcome_admin() three-source authorization
  - DM / channel / both delivery
  - Per-config DB helpers (set/get/clear/admins/welcomed)

Imported as a sibling by command.py (relative import) and from matterbot.py
via the package path commands/welcome -> welcome.welcome.
"""

import logging
import sqlite3
import threading
import time

try:
    # When loaded inside the bot's module loader, the package is `welcome`
    # (the directory name lower-cased) and defaults is alongside.
    from . import defaults  # type: ignore[import-not-found]
except ImportError:
    # When matterbot.py imports us directly via `welcome.welcome`, the
    # relative import above doesn't work because we aren't running inside
    # a package context. Fall back to the absolute path the loader uses.
    import defaults  # type: ignore[import-not-found,no-redef]

log = logging.getLogger('matterbot')

# Single lock for write paths. SQLite's own file lock would also work,
# but at the WAL+per-call-connection scale we have, an in-process lock
# is simpler and avoids retry-on-SQLITE_BUSY noise.
_write_lock = threading.Lock()


def _connect():
    """Open a fresh SQLite connection. We don't share connections across
    threads — the cost is microseconds and it sidesteps SQLite's
    same-thread enforcement entirely."""
    conn = sqlite3.connect(defaults.DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema():
    """Create tables on first run. Idempotent. Called once at module-load
    time below — operators don't have to do anything to bootstrap."""
    with _write_lock:
        conn = _connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS welcome_configs (
                    channel_id    TEXT PRIMARY KEY,
                    channel_name  TEXT NOT NULL,
                    message       TEXT NOT NULL,
                    delivery      TEXT NOT NULL DEFAULT 'dm',
                    public_greet  TEXT,
                    enabled       INTEGER NOT NULL DEFAULT 1,
                    updated_at    TEXT NOT NULL,
                    updated_by    TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS welcomed_users (
                    channel_id   TEXT NOT NULL,
                    user_id      TEXT NOT NULL,
                    welcomed_at  TEXT NOT NULL,
                    PRIMARY KEY (channel_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS channel_admins (
                    channel_id  TEXT NOT NULL,
                    user_id     TEXT NOT NULL,
                    added_at    TEXT NOT NULL,
                    added_by    TEXT NOT NULL,
                    PRIMARY KEY (channel_id, user_id)
                );
            """)
            conn.commit()
        finally:
            conn.close()


def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


# ----- config CRUD -----------------------------------------------------------

def get_config(channel_id):
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT channel_id, channel_name, message, delivery, public_greet, "
            "       enabled, updated_at, updated_by "
            "FROM welcome_configs WHERE channel_id = ?",
            (channel_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def set_config(channel_id, channel_name, message, delivery, public_greet, updated_by):
    with _write_lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO welcome_configs "
                "    (channel_id, channel_name, message, delivery, public_greet, "
                "     enabled, updated_at, updated_by) "
                "VALUES (?, ?, ?, ?, ?, 1, ?, ?) "
                "ON CONFLICT(channel_id) DO UPDATE SET "
                "    channel_name = excluded.channel_name, "
                "    message      = excluded.message, "
                "    delivery     = excluded.delivery, "
                "    public_greet = excluded.public_greet, "
                "    enabled      = 1, "
                "    updated_at   = excluded.updated_at, "
                "    updated_by   = excluded.updated_by",
                (channel_id, channel_name, message, delivery, public_greet,
                 _now(), updated_by),
            )
            conn.commit()
        finally:
            conn.close()


def clear_config(channel_id):
    with _write_lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM welcome_configs WHERE channel_id = ?", (channel_id,))
            conn.commit()
        finally:
            conn.close()


def list_configs():
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT channel_id, channel_name, delivery, enabled, updated_at, updated_by "
            "FROM welcome_configs ORDER BY channel_name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ----- welcomed-users tracking ----------------------------------------------

def mark_welcomed(channel_id, user_id):
    """Insert into welcomed_users. Returns True if newly inserted, False if
    the row already existed (idempotent — duplicate join events are a no-op)."""
    with _write_lock:
        conn = _connect()
        try:
            cur = conn.execute(
                "INSERT OR IGNORE INTO welcomed_users (channel_id, user_id, welcomed_at) "
                "VALUES (?, ?, ?)",
                (channel_id, user_id, _now()),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def is_welcomed(channel_id, user_id):
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT 1 FROM welcomed_users WHERE channel_id = ? AND user_id = ?",
            (channel_id, user_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def reset_welcomed(channel_id, user_id=None):
    with _write_lock:
        conn = _connect()
        try:
            if user_id is None:
                conn.execute("DELETE FROM welcomed_users WHERE channel_id = ?", (channel_id,))
            else:
                conn.execute(
                    "DELETE FROM welcomed_users WHERE channel_id = ? AND user_id = ?",
                    (channel_id, user_id),
                )
            conn.commit()
        finally:
            conn.close()


# ----- per-channel admin allowlist ------------------------------------------

def add_channel_admin(channel_id, user_id, added_by):
    with _write_lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO channel_admins "
                "    (channel_id, user_id, added_at, added_by) "
                "VALUES (?, ?, ?, ?)",
                (channel_id, user_id, _now(), added_by),
            )
            conn.commit()
        finally:
            conn.close()


def remove_channel_admin(channel_id, user_id):
    with _write_lock:
        conn = _connect()
        try:
            conn.execute(
                "DELETE FROM channel_admins WHERE channel_id = ? AND user_id = ?",
                (channel_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()


def list_channel_admins(channel_id):
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT user_id, added_at, added_by FROM channel_admins "
            "WHERE channel_id = ? ORDER BY added_at",
            (channel_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def is_channel_allowlisted(channel_id, user_id):
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT 1 FROM channel_admins WHERE channel_id = ? AND user_id = ?",
            (channel_id, user_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


# ----- three-source authorization -------------------------------------------

def _user_has_system_admin(mmDriver, user_id):
    try:
        userinfo = mmDriver.users.get_user(user_id)
        roles = [r.lower() for r in userinfo.get('roles', '').split()]
        return 'system_admin' in roles
    except Exception:
        log.exception(f"welcome: get_user({user_id}) failed during admin check")
        return False


def _user_has_channel_admin(mmDriver, channel_id, user_id):
    try:
        member = mmDriver.channels.get_channel_member(channel_id, user_id)
        roles = [r.lower() for r in member.get('roles', '').split()]
        return 'channel_admin' in roles
    except Exception:
        # 404 if the user isn't a member — not an error, just "no"
        return False


def is_welcome_admin(mmDriver, user_id, channel_id):
    """Three-source any-of check. Order is by cost: cheapest first.

    1. system_admin role (one users.get_user call — often already cached)
    2. channel_admin role on the target channel (one members call)
    3. per-channel allowlist (one SQLite lookup)
    """
    if _user_has_system_admin(mmDriver, user_id):
        return True
    if _user_has_channel_admin(mmDriver, channel_id, user_id):
        return True
    if is_channel_allowlisted(channel_id, user_id):
        return True
    return False


# ----- delivery -------------------------------------------------------------

def _get_or_create_direct_channel(mmDriver, my_id, target_user_id):
    """Wrap the mattermostdriver direct-message-channel creator. Method
    name has varied across driver versions; try the canonical and fall
    back to the older alias."""
    options = [my_id, target_user_id]
    channels_api = mmDriver.channels
    if hasattr(channels_api, 'create_direct_message_channel'):
        return channels_api.create_direct_message_channel(options=options)
    if hasattr(channels_api, 'create_direct_channel'):
        return channels_api.create_direct_channel(options=options)
    raise RuntimeError("mattermostdriver: no direct-message-channel creator")


def _render(template, user_mention):
    if not template:
        return template
    return template.replace('{user}', user_mention)


def _resolve_user_mention(mmDriver, user_id):
    try:
        username = mmDriver.users.get_user(user_id).get('username') or user_id
    except Exception:
        username = user_id
    return f"@{username}"


def deliver(mmDriver, my_id, user_id, channel_id, config):
    """Try to deliver the configured welcome to the user. Returns True on
    any successful delivery (DM or channel post), False on total failure.

    Caller uses the return value to decide whether to mark the user as
    welcomed — total failures should leave them unmarked so the next
    sighting retries."""
    message = config['message']
    delivery = config['delivery']
    public_greet = config.get('public_greet') or ''
    user_mention = _resolve_user_mention(mmDriver, user_id)
    rendered_msg = _render(message, user_mention)
    rendered_greet = _render(public_greet, user_mention) or f"Welcome {user_mention}!"

    delivered = False

    if delivery in ('dm', 'both'):
        try:
            dm = _get_or_create_direct_channel(mmDriver, my_id, user_id)
            mmDriver.posts.create_post(options={
                'channel_id': dm['id'],
                'message': rendered_msg,
            })
            delivered = True
        except Exception:
            log.exception(
                f"welcome: DM delivery failed user={user_id} channel={channel_id}"
            )

    if delivery in ('channel', 'both'):
        try:
            text = rendered_greet if delivery == 'both' else rendered_msg
            mmDriver.posts.create_post(options={
                'channel_id': channel_id,
                'message': text,
            })
            delivered = True
        except Exception:
            log.exception(
                f"welcome: channel post failed user={user_id} channel={channel_id}"
            )

    return delivered


# ----- on_join event handler ------------------------------------------------

def on_join(mmDriver, my_id, user_id, channel_id):
    """Called from matterbot.py when a user joins a channel the bot can see.

    Idempotent and synchronous. Designed to be dispatched off the asyncio
    event loop via loop.run_in_executor — does its own SQLite I/O and
    HTTP calls without yielding."""
    if not user_id or not channel_id:
        return
    if user_id == my_id:
        return  # bot's own join

    if is_welcomed(channel_id, user_id):
        return

    config = get_config(channel_id)

    if config is None or not config.get('enabled'):
        # No welcome configured — but still record the sighting so a future
        # `@welcome set` on this channel doesn't spam existing members.
        mark_welcomed(channel_id, user_id)
        return

    if deliver(mmDriver, my_id, user_id, channel_id, config):
        mark_welcomed(channel_id, user_id)
    # else: leave unmarked so the next sighting retries delivery


# ----- reconcile (called from matterbot.py:run_forever before each WS connect)

def reconcile(mmDriver, my_id):
    """Walk every configured channel, fetch its members, and on_join() any
    user we haven't welcomed yet. Catches joins that happened while the
    bot was offline."""
    try:
        configs = list_configs()
    except Exception:
        log.exception("welcome.reconcile: list_configs failed")
        return

    for cfg in configs:
        channel_id = cfg['channel_id']
        try:
            page = 0
            while True:
                members = mmDriver.channels.get_channel_members(
                    channel_id, params={'page': page, 'per_page': 200},
                )
                if not members:
                    break
                for member in members:
                    member_user_id = member.get('user_id')
                    if not member_user_id:
                        continue
                    try:
                        on_join(mmDriver, my_id, member_user_id, channel_id)
                    except Exception:
                        log.exception(
                            f"welcome.reconcile: on_join failed "
                            f"user={member_user_id} channel={channel_id}"
                        )
                page += 1
        except Exception:
            log.exception(f"welcome.reconcile: channel {channel_id} member fetch failed")


# ----- module-load-time bootstrap -------------------------------------------

# Create the SQLite schema on first import. Cheap (IF NOT EXISTS), idempotent,
# and means operators don't have to run a separate migration step.
try:
    init_schema()
except Exception:
    log.exception("welcome: init_schema failed at import time")
