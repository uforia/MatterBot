#!/usr/bin/env python3

"""@welcome subcommand handler.

Dispatches `@welcome <sub> [args]` against the shared welcome.py helpers.
All authorization is delegated to welcome.is_welcome_admin (three-source
any-of: system_admin role, channel_admin role on this channel, or per-
channel allowlist).
"""

import logging
import re

log = logging.getLogger('MatterBot')

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

# Sibling shared module — see welcome.py for DB, auth, delivery, on_join.
from . import welcome as wm


# ----- caller resolution ----------------------------------------------------
# process() receives `channel` (NAME) and `username`. We need the IDs to
# scope DB rows and to call the Mattermost API. Look them up via conn.

def _resolve_caller(conn, channel_name, username, team_id=None):
    """Returns (user_id, channel_id) for the @welcome invocation, or
    (None, None) on lookup failure. Best-effort: any API error surfaces
    as None and the caller emits a generic 'could not resolve' reply.

    Mattermost's WS post events expose `sender_name` as `@<username>`
    (with the @ prefix). The users.get_user_by_username API expects the
    bare username — the @ is rejected by username validation and the
    server returns 404 ("Sorry, we could not find the page."). Strip
    leading @s before the lookup."""
    bare_username = username.lstrip('@')
    try:
        user_id = conn.users.get_user_by_username(bare_username)['id']
    except Exception as e:
        log.warning(f"welcome: get_user_by_username({bare_username!r}) failed: {e}")
        return None, None
    try:
        if team_id is None:
            # Fall back to the bot's "me" team — slightly chatty but
            # safe; the alternative is threading team_id through
            # call_module's signature, which is a bigger change.
            me = conn.users.get_user('me')
            # Method name varies across mattermostdriver versions; try
            # the canonical names in order before giving up.
            teams = None
            teams_api = conn.teams
            for method_name in ('get_user_teams', 'get_teams_for_user'):
                method = getattr(teams_api, method_name, None)
                if method is not None:
                    try:
                        teams = method(me['id'])
                        break
                    except Exception:
                        continue
            team_id = teams[0]['id'] if teams else None
        if not team_id:
            log.warning(f"welcome: could not resolve a team_id for channel={channel_name!r}")
            return user_id, None
        chan = conn.channels.get_channel_by_name(team_id, channel_name)
        return user_id, chan['id']
    except Exception as e:
        log.warning(f"welcome: channel lookup failed channel={channel_name!r}: {e}")
        return user_id, None


# ----- mention parsing ------------------------------------------------------

_USER_MENTION_RX = re.compile(r'^@([A-Za-z0-9._\-]+)$')


def _resolve_mention(conn, mention):
    """Take an @username token (with leading @) and return the user_id, or
    None if it doesn't resolve. Used by `@welcome admin add @alice`."""
    m = _USER_MENTION_RX.match(mention.strip())
    if not m:
        return None
    try:
        return conn.users.get_user_by_username(m.group(1))['id']
    except Exception:
        return None


# ----- subcommand handlers --------------------------------------------------

def _sub_set(conn, args, channel_id, channel_name, user_id):
    if not args:
        return "Usage: `@welcome set <message>`. Markdown allowed. `{user}` expands to the joining user's mention."
    message = ' '.join(args).strip()
    if len(message) > settings.MAX_MESSAGE_LEN:
        return f"Welcome message too long ({len(message)} chars; max {settings.MAX_MESSAGE_LEN})."

    existing = wm.get_config(channel_id)
    delivery = existing['delivery'] if existing else settings.DEFAULT_DELIVERY
    public_greet = existing['public_greet'] if existing else None

    wm.set_config(channel_id, channel_name, message, delivery, public_greet, user_id)

    # Bootstrap: mark all current channel members as welcomed so newly
    # configuring on a long-lived channel does not flood existing users.
    bootstrap_marked = 0
    try:
        page = 0
        while True:
            members = conn.channels.get_channel_members(
                channel_id, params={'page': page, 'per_page': 200},
            )
            if not members:
                break
            for member in members:
                mid = member.get('user_id')
                if mid and wm.mark_welcomed(channel_id, mid):
                    bootstrap_marked += 1
            page += 1
    except Exception:
        # Non-fatal — the welcome is stored, but we could not mark all
        # current members. Reconcile-on-reconnect will catch up.
        return (f"Welcome stored. **Warning:** could not enumerate existing channel "
                f"members to mark them as already-welcomed. They may be DM'd on the "
                f"next reconcile pass.")
    return f"Welcome stored for `#{channel_name}` ({bootstrap_marked} existing members silently marked as already-welcomed, delivery=`{delivery}`)."


def _sub_get(channel_id, channel_name):
    cfg = wm.get_config(channel_id)
    if not cfg:
        return f"No welcome configured for `#{channel_name}`."
    delivery = cfg['delivery']
    greet = cfg.get('public_greet') or '_(none)_'
    return (
        f"**Welcome config for `#{channel_name}`**\n\n"
        f"- Delivery: `{delivery}`\n"
        f"- Public greet: {greet}\n"
        f"- Updated at: `{cfg['updated_at']}` by `{cfg['updated_by']}`\n\n"
        f"**Message:**\n\n{cfg['message']}"
    )


def _sub_clear(channel_id, channel_name):
    if not wm.get_config(channel_id):
        return f"No welcome configured for `#{channel_name}` — nothing to clear."
    wm.clear_config(channel_id)
    return f"Welcome cleared for `#{channel_name}`. Welcomed-users history retained."


def _sub_delivery(args, channel_id, channel_name, user_id):
    if not args or args[0].lower() not in ('dm', 'channel', 'both'):
        return "Usage: `@welcome delivery <dm|channel|both>`"
    mode = args[0].lower()
    cfg = wm.get_config(channel_id)
    if not cfg:
        return f"No welcome configured for `#{channel_name}` — `@welcome set <message>` first."
    wm.set_config(
        channel_id, channel_name, cfg['message'], mode, cfg.get('public_greet'), user_id,
    )
    return f"Delivery mode for `#{channel_name}` set to `{mode}`."


def _sub_greet(args, channel_id, channel_name, user_id):
    cfg = wm.get_config(channel_id)
    if not cfg:
        return f"No welcome configured for `#{channel_name}` — `@welcome set <message>` first."
    text = ' '.join(args).strip() or None
    wm.set_config(
        channel_id, channel_name, cfg['message'], cfg['delivery'], text, user_id,
    )
    if text is None:
        return f"Public greet cleared for `#{channel_name}`."
    return f"Public greet for `#{channel_name}` set to: {text}"


def _sub_test(conn, my_id, channel_id, channel_name, user_id):
    cfg = wm.get_config(channel_id)
    if not cfg:
        return f"No welcome configured for `#{channel_name}` — nothing to test."
    # Use the caller as the recipient. Does NOT mark them as welcomed
    # (so a real future join still triggers normally).
    ok = wm.deliver(conn, my_id, user_id, channel_id, cfg)
    if ok:
        return f"Test welcome delivered to you per the `{cfg['delivery']}` config. (Your welcomed-state is unchanged.)"
    return f"Test welcome FAILED for `#{channel_name}`. Check the bot logs for the API error."


def _sub_list(conn):
    rows = wm.list_configs()
    if not rows:
        return "No welcome configs anywhere."
    lines = [
        "| Channel | Delivery | Enabled | Updated by | Updated at |",
        "| :- | :- | :- | :- | :- |",
    ]
    for r in rows:
        chan = r['channel_name'] or r['channel_id']
        lines.append(
            f"| `{chan}` | `{r['delivery']}` | "
            f"{'yes' if r['enabled'] else 'no'} | `{r['updated_by']}` | `{r['updated_at']}` |"
        )
    return "\n".join(lines)


def _sub_reset(conn, args, channel_id, channel_name):
    if not args:
        wm.reset_welcomed(channel_id)
        return f"Welcomed-state cleared for ALL users in `#{channel_name}`. They will be re-welcomed on next sighting."
    target_id = _resolve_mention(conn, args[0])
    if not target_id:
        return f"Could not resolve `{args[0]}` to a user — use `@username`."
    wm.reset_welcomed(channel_id, target_id)
    return f"Welcomed-state cleared for {args[0]} in `#{channel_name}`."


def _sub_admin(conn, args, channel_id, channel_name, caller_user_id):
    if not args:
        return "Usage: `@welcome admin <add|remove|list> [@user]`"
    op = args[0].lower()
    if op == 'list':
        rows = wm.list_channel_admins(channel_id)
        if not rows:
            return f"No per-channel admins for `#{channel_name}` (system_admin + channel_admin roles still apply)."
        try:
            names = []
            for r in rows:
                try:
                    u = conn.users.get_user(r['user_id'])
                    names.append(f"@{u['username']}")
                except Exception:
                    names.append(f"`{r['user_id']}`")
            return f"Per-channel admins for `#{channel_name}`: " + ', '.join(names)
        except Exception:
            return f"Per-channel admin user_ids for `#{channel_name}`: " + ', '.join(f"`{r['user_id']}`" for r in rows)
    if op in ('add', 'remove'):
        if len(args) < 2:
            return f"Usage: `@welcome admin {op} @user`"
        target_id = _resolve_mention(conn, args[1])
        if not target_id:
            return f"Could not resolve `{args[1]}` to a user — use `@username`."
        if op == 'add':
            wm.add_channel_admin(channel_id, target_id, caller_user_id)
            return f"Added {args[1]} to the per-channel admin allowlist for `#{channel_name}`."
        else:
            wm.remove_channel_admin(channel_id, target_id)
            return f"Removed {args[1]} from the per-channel admin allowlist for `#{channel_name}`."
    return f"Unknown admin subcommand `{op}`. Use `add`, `remove`, or `list`."


# ----- process() entry point -------------------------------------------------

def process(command, channel, username, params, files, conn):
    try:
        messages = []

        # Resolve who and where.
        user_id, channel_id = _resolve_caller(conn, channel, username)
        if not user_id or not channel_id:
            messages.append({'text': "Could not resolve caller user / channel via the Mattermost API. Try again, or check the bot logs."})
            return {'messages': messages}

        # Authorize. Same gate for every subcommand.
        try:
            my_id = conn.users.get_user('me')['id']
        except Exception:
            messages.append({'text': "Internal error: bot could not resolve its own user id."})
            return {'messages': messages}

        if not wm.is_welcome_admin(conn, user_id, channel_id):
            messages.append({'text': "Not authorized. `@welcome` requires system_admin role, channel_admin on this channel, or membership in the per-channel allowlist."})
            return {'messages': messages}

        # Dispatch.
        if not params:
            messages.append({'text':
                "Usage: `@welcome <subcommand> [args]`\n\n"
                "Subcommands: `set <message>`, `get`, `clear`, "
                "`delivery <dm|channel|both>`, `greet <text>`, `test`, `list`, "
                "`reset [@user]`, `admin add|remove|list [@user]`."})
            return {'messages': messages}

        sub = params[0].lower()
        args = params[1:]

        if sub == 'set':
            text = _sub_set(conn, args, channel_id, channel, user_id)
        elif sub == 'get':
            text = _sub_get(channel_id, channel)
        elif sub == 'clear':
            text = _sub_clear(channel_id, channel)
        elif sub == 'delivery':
            text = _sub_delivery(args, channel_id, channel, user_id)
        elif sub == 'greet':
            text = _sub_greet(args, channel_id, channel, user_id)
        elif sub == 'test':
            text = _sub_test(conn, my_id, channel_id, channel, user_id)
        elif sub == 'list':
            text = _sub_list(conn)
        elif sub == 'reset':
            text = _sub_reset(conn, args, channel_id, channel)
        elif sub == 'admin':
            text = _sub_admin(conn, args, channel_id, channel, user_id)
        else:
            text = (f"Unknown subcommand `{sub}`. Run `@welcome` with no args "
                    f"to see the usage line.")

        messages.append({'text': text})
        return {'messages': messages}
    except Exception as e:
        return {'messages': [{'text': f"`@welcome` internal error: `{e}`. See bot logs for traceback."}]}
