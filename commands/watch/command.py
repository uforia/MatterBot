#!/usr/bin/env python3

import logging
import re
import time

log = logging.getLogger("MatterBot")

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path

_pkg = __package__ or Path(__file__).parent.name


def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None


_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
### Loader end, actual module functionality starts here

# Import the store under the same package-aware loader so it works whether
# matterbot is launched from the project root (commands on sys.path as a
# flat namespace) or as a package (commands.watch.store).
_store = _load("store")
if _store is None:
    # Should never happen — store.py ships in the same directory as this
    # module. If it does, the command degrades to "no-op with clear error"
    # rather than crashing module load.
    log.error("watch: store.py could not be imported; @watch will be a no-op")

# Duration grammar: <integer><unit> where unit is s/m/h/d/w.
_DURATION_RE = re.compile(r"^(\d{1,7})([smhdw])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 7 * 86400}

# Keyword sanity check. Allow alnum + a handful of OSINT-friendly punctuation
# (cve identifiers, hashes-as-strings, hyphenated names). Rejects whitespace,
# wildcards, and shell metacharacters so the store can never carry a regex
# special by accident — match is plain `in` substring, but defensive shape
# keeps the JSON file inspectable.
_KEYWORD_RE = re.compile(r"^[A-Za-z0-9._\-:/+@]+$")


def _parse_duration(token):
    """Return (seconds, error_message). seconds=None means 'never'."""
    if token is None:
        return None, None
    token = token.strip().lower()
    if token in ("never", "permanent", "infinite", "0"):
        return None, None
    m = _DURATION_RE.match(token)
    if not m:
        return False, (
            f"`{token}` is not a duration. Use `<number><unit>` where unit is "
            "`s`/`m`/`h`/`d`/`w`, or `never`. Example: `7d`."
        )
    value = int(m.group(1))
    unit = m.group(2)
    seconds = value * _UNIT_SECONDS[unit]
    if seconds <= 0:
        return False, "Duration must be positive."
    if seconds > settings.MAX_DURATION_SECONDS:
        max_days = settings.MAX_DURATION_SECONDS // 86400
        return False, f"Duration too long. Max is {max_days}d."
    return seconds, None


def _format_relative(target_ts, now=None):
    if target_ts is None:
        return "never expires"
    if now is None:
        now = int(time.time())
    delta = target_ts - now
    if delta <= 0:
        return "expired"
    if delta < 60:
        return f"expires in {delta}s"
    if delta < 3600:
        return f"expires in {delta // 60}m"
    if delta < 86400:
        h = delta // 3600
        m = (delta % 3600) // 60
        return f"expires in {h}h {m:02d}m"
    days = delta // 86400
    hours = (delta % 86400) // 3600
    return f"expires in {days}d {hours}h"


def _validate_keyword(raw):
    if len(raw) < settings.MIN_KEYWORD_LEN:
        return None, (
            f"Keyword must be at least {settings.MIN_KEYWORD_LEN} characters."
        )
    if len(raw) > settings.MAX_KEYWORD_LEN:
        return None, (
            f"Keyword must be at most {settings.MAX_KEYWORD_LEN} characters."
        )
    if not _KEYWORD_RE.match(raw):
        return None, (
            "Keyword may only contain letters, digits, and `._-:/+@`. "
            "Wildcards and whitespace are not supported."
        )
    return raw.lower(), None


def _resolve_userid(username, conn):
    """Map @username (with or without leading @) to a Mattermost userid.

    process() receives username as a string only; the bot does not pass us
    the userid. We look it up via mmDriver so the store key is the stable
    opaque id, not the mutable username.
    """
    try:
        clean = username.lstrip("@")
        return conn.users.get_user_by_username(clean)["id"]
    except Exception:
        log.exception("watch: failed to resolve userid for %r", username)
        return None


def _cmd_list(userid):
    rows = _store.list_for_user(userid)
    if not rows:
        return "You have no active watches. Add one with `@watch add <keyword> [duration]`."
    now = int(time.time())
    lines = [f"## Your active watches ({len(rows)})"]
    for kw, exp in rows:
        lines.append(f"  {kw:<32}  {_format_relative(exp, now)}")
    return "```\n" + "\n".join(lines) + "\n```"


def _cmd_add(userid, params):
    if not params:
        return (
            "Usage: `@watch add <keyword> [duration]`. "
            "Example: `@watch add ransomware 7d`."
        )
    keyword_raw = params[0]
    keyword, err = _validate_keyword(keyword_raw)
    if err:
        return err
    duration_token = params[1] if len(params) > 1 else settings.DEFAULT_DURATION
    seconds, err = _parse_duration(duration_token)
    if err is not None and seconds is False:
        return err
    expiry = None if seconds is None else int(time.time()) + seconds
    ok, reason = _store.add(userid, keyword, expiry, settings.MAX_WATCHES_PER_USER)
    if not ok:
        return f"Could not add `{keyword}`: {reason}."
    when = _format_relative(expiry)
    verb = "Updated" if reason == "replaced" else "Watching"
    return f"{verb} `{keyword}` ({when})."


def _cmd_del(userid, params):
    if not params:
        return "Usage: `@watch del <keyword>`."
    keyword, err = _validate_keyword(params[0])
    if err:
        return err
    if _store.delete(userid, keyword):
        return f"Stopped watching `{keyword}`."
    return f"You were not watching `{keyword}`."


def _cmd_clear(userid):
    count = _store.clear(userid)
    if not count:
        return "You had no active watches."
    return f"Cleared {count} watch(es)."


def process(command, channel, username, params, files, conn):
    if _store is None:
        return {
            "messages": [
                {
                    "text": "Watch store is not available — module deployment "
                    "is incomplete (store.py missing)."
                }
            ]
        }

    userid = _resolve_userid(username, conn)
    if userid is None:
        return {
            "messages": [
                {
                    "text": "Could not resolve your Mattermost user id. "
                    "Cannot manage watches. Check bot logs."
                }
            ]
        }

    if not params:
        reply = _cmd_list(userid)
    else:
        sub = params[0].lower()
        rest = params[1:]
        if sub == "list":
            reply = _cmd_list(userid)
        elif sub == "add":
            reply = _cmd_add(userid, rest)
        elif sub in ("del", "delete", "remove", "rm"):
            reply = _cmd_del(userid, rest)
        elif sub == "clear":
            reply = _cmd_clear(userid)
        else:
            # Bare `@watch <keyword>` shorthand for `add <keyword>` — convenient
            # for the common case where the user just wants to add one thing
            # without remembering the subcommand.
            reply = _cmd_add(userid, params)

    return {"messages": [{"text": reply}]}


# ---------------------------------------------------------------------------
# Scan hook — called by matterbot.py for every non-self channel post.
# Runs in the bot's ThreadPoolExecutor (see matterbot.py:_command_executor)
# so blocking on the Mattermost REST API here is fine; it will not stall
# the asyncio event loop.
# ---------------------------------------------------------------------------


def _channel_member_ids(conn, chanid):
    """Page through channel members, returning a set of user ids.

    Mattermost's get_channel_members caps at 200 per page. Channels with
    more than a few hundred members will pay multiple round trips, which is
    why this is on the threadpool path.
    """
    members = set()
    page = 0
    while True:
        try:
            chunk = conn.channels.get_channel_members(
                chanid, params={"page": page, "per_page": 200}
            )
        except Exception:
            log.exception("watch: get_channel_members failed for %s", chanid)
            return members
        if not chunk:
            break
        for m in chunk:
            uid = m.get("user_id")
            if uid:
                members.add(uid)
        if len(chunk) < 200:
            break
        page += 1
    return members


def _send_alert(conn, myid, watcher_userid, watcher_keyword, post_data):
    """Open (or fetch) the DM channel with the watcher and post the alert."""
    try:
        dm = conn.channels.create_direct_message_channel([myid, watcher_userid])
    except Exception:
        log.exception(
            "watch: could not open DM with %s for alert on %r",
            watcher_userid,
            watcher_keyword,
        )
        return

    dm_chanid = dm.get("id")
    if not dm_chanid:
        return

    snippet = post_data["message"]
    if len(snippet) > settings.SNIPPET_CHARS:
        snippet = snippet[: settings.SNIPPET_CHARS] + "…"

    # The snippet is another user's chat message. Without sanitisation, any
    # channel user could embed `@channel`/`@here` in a post that triggers
    # someone's watcher and the bot would faithfully render the mention as
    # a live ping inside the DM alert. Strip backticks/pipes/newlines so
    # the inline-code wrap below holds, then render inside it so Mattermost
    # suppresses @-mentions and markdown-link interpretation.
    safe_snippet = snippet.replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')

    text = (
        f"🔔 Watch hit: `{watcher_keyword}`\n"
        f"Channel: ~{post_data['channame']}\n"
        f"From:    @{post_data['author']}\n\n"
        f"> `{safe_snippet}`"
    )

    try:
        conn.posts.create_post(options={"channel_id": dm_chanid, "message": text})
    except Exception:
        log.exception(
            "watch: failed to post alert DM for %s on %r",
            watcher_userid,
            watcher_keyword,
        )


def scan_message(conn, myid, author_userid, chanid, channame, author_username, message):
    """Fire-and-forget scanner. Called by matterbot.handle_post.

    Args mirror the welcome.on_join hook style — bare primitives so this can
    be invoked through run_in_executor without pickling any module state.
    """
    if _store is None or not message:
        return
    if author_userid == myid:
        # Bot's own messages are already excluded by handle_post's recursion
        # guard for most installs, but be defensive — alerting yourself on
        # your own bot posts is a feedback loop waiting to happen.
        return

    active = _store.iter_active()
    if not active:
        return

    message_lower = message.lower()
    # Collect distinct watchers whose keyword matched; one alert per watcher
    # even if they have multiple keywords in the same message.
    hits: dict[str, str] = {}
    for watcher_userid, keyword in active:
        if watcher_userid == author_userid:
            # Don't alert someone on their own messages.
            continue
        if keyword in message_lower and watcher_userid not in hits:
            hits[watcher_userid] = keyword

    if not hits:
        return

    # Only alert watchers who can actually see this channel — never leak
    # private/restricted-channel content to someone not in the channel.
    members = _channel_member_ids(conn, chanid)

    post_data = {
        "channame": channame,
        "author": author_username,
        "message": message,
    }

    for watcher_userid, keyword in hits.items():
        if watcher_userid not in members:
            continue
        _send_alert(conn, myid, watcher_userid, keyword, post_data)
