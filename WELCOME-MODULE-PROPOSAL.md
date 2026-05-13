# Welcome Module Proposal

A welcome-message module for MatterBot that configures per-channel rules via `@welcome` admin commands and force-pushes them to new joiners via DM (with optional public greet) on the first time the bot sees them in a configured channel.

## Requirements

- Configurable welcome message per public **or** private channel.
- Configuration survives bot restart.
- Triggered on the first time a user joins each channel — never re-triggers on re-join.
- Force-push delivery so the rules cannot be missed.

## File layout

```
commands/welcome/
├── command.py        # @welcome subcommands (set/get/list/clear/test/admin add|remove|list/...)
├── defaults.py       # DB path, default delivery mode (no static admin list — auth is live)
├── welcome.py        # Shared module: DB schema, state queries, join-handler entry point, auth checks
└── state.db          # SQLite, created on first write (gitignored)
```

Plus a small hook in `matterbot.py` to wire join events into the handler. That is the only `matterbot.py` change.

## Data model — SQLite, single file

Location: `commands/welcome/state.db` (lives next to `command.py` / `defaults.py` in the module directory).

```sql
CREATE TABLE welcome_configs (
    channel_id    TEXT PRIMARY KEY,
    channel_name  TEXT NOT NULL,         -- snapshot for /list readability, refreshed on touch
    message       TEXT NOT NULL,         -- markdown; supports {user} placeholder
    delivery      TEXT NOT NULL DEFAULT 'dm',  -- 'dm' | 'channel' | 'both'
    public_greet  TEXT,                  -- optional short channel post when delivery in ('channel','both')
    enabled       INTEGER NOT NULL DEFAULT 1,
    updated_at    TEXT NOT NULL,
    updated_by    TEXT NOT NULL
);

CREATE TABLE welcomed_users (
    channel_id   TEXT NOT NULL,
    user_id      TEXT NOT NULL,
    welcomed_at  TEXT NOT NULL,
    PRIMARY KEY (channel_id, user_id)
);

CREATE TABLE channel_admins (
    channel_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    added_at    TEXT NOT NULL,
    added_by    TEXT NOT NULL,
    PRIMARY KEY (channel_id, user_id)
);
```

SQLite over shelve because: queryable, concurrent-safe within a process, ACID on writes. Single file. Matches the "survives restart" requirement trivially. The `channel_admins` table stores the per-channel explicit allowlist (see Authorization below).

## Trigger surface — three event sources, one handler

In `matterbot.py`:

1. **`posted` event** with `post['type'] == 'system_join_channel'` — user self-joins a public channel.
2. **`user_added` event** — user added by someone else (private channel invite, admin-add, etc.).
3. **On WS reconnect / bot startup** — reconcile pass: for each row in `welcome_configs`, `GET /api/v4/channels/{channel_id}/members`, diff against `welcomed_users`, welcome anyone new.

All three call `welcome.on_join(user_id, channel_id)`. That function:

```
1. If user_id == self.my_user_id → return (don't welcome the bot)
2. If welcomed_users has (channel_id, user_id) → return (already welcomed)
3. If welcome_configs has (channel_id, enabled=1) → send message
4. Insert into welcomed_users  ← always insert, even if no config existed,
                                  so configuring a welcome later does NOT
                                  spam existing members
```

That last point is the key correctness detail: **insert into `welcomed_users` for every join event we see, regardless of whether a welcome is configured**. This way, when an admin later runs `@welcome set` on a long-lived channel, existing members are already marked and only future joiners get the message.

To handle the "channel that existed before the bot did" case: the first time a channel gets a welcome configured, run the reconcile pass once and mark all current members as welcomed (silently). Default behavior — opt-in flag `--also-existing` if the admin actually wants to welcome retroactively.

## Admin commands — `@welcome`

| Command | Action |
|---|---|
| `@welcome set <message>` | Set/update welcome for the **current** channel (channel inferred from command context — no need to type channel name). Marks all existing members as welcomed silently. |
| `@welcome get` | Show current welcome config for this channel. |
| `@welcome clear` | Remove welcome config for this channel. Does NOT clear `welcomed_users` history. |
| `@welcome delivery <dm\|channel\|both>` | Change delivery mode for this channel. |
| `@welcome greet <text>` | Set the public greet line (used when delivery includes a channel post). Empty arg removes it. |
| `@welcome test` | Send the configured welcome to the invoker, as a dry-run. Does NOT mark welcomed. |
| `@welcome list` | DM the invoker a table of all configured channels. |
| `@welcome reset [@user]` | Clear welcomed-state for this channel (or just one user). Next sighting re-triggers. |
| `@welcome admin add @user` | Add a user to the per-channel admin allowlist for the **current** channel. |
| `@welcome admin remove @user` | Remove a user from the per-channel admin allowlist for the current channel. |
| `@welcome admin list` | Show the per-channel admin allowlist for the current channel. |

Channel reference defaults to *the channel the command was typed in*. Removes a whole class of "lookup channel by name" complexity.

### Authorization — three sources, any-of

Every `@welcome` subcommand checks `is_welcome_admin(user_id, channel_id)`, which passes if **any** of the following hold:

1. **User holds the `system_admin` Mattermost role** (global super-admin). Always allowed, regardless of channel membership or per-channel allowlist.
2. **User holds the `channel_admin` Mattermost role for the target channel.** Resolved via `GET /api/v4/channels/{channel_id}/members/{user_id}` — the returned `roles` field carries the channel-scoped roles. A 404 (user not a channel member) is treated as "no" and falls through to the next check rather than erroring.
3. **User is in the per-channel allowlist** stored in the `channel_admins` SQLite table for that specific `channel_id`. Managed at runtime via the `@welcome admin add/remove/list` subcommands.

Order matters for cost: check role (1) first since it's a single API call already cached on most paths; check (2) only if (1) fails (one extra API call); check (3) only if (2) fails (one local SQLite lookup). The result is cached per `(user_id, channel_id)` tuple inside one command invocation so the three commands `@welcome set ... ; @welcome greet ... ; @welcome delivery dm` from the same user in the same channel don't hammer the API.

**Bootstrap:** when a brand-new channel has no per-channel allowlist entries yet, only `system_admin` or the channel's `channel_admin` can call `@welcome admin add` to seed it. This matches Mattermost's native pattern — channel admins designate their own delegates.

**Bot rejection on failed auth:** single-line "not authorized" reply in the same channel where the command was typed. No state change, nothing logged beyond a single DEBUG line (we don't want to give a probe-anyone helpful info about which check failed).

`defaults.py` no longer ships an `ADMIN_USERS` list. The shipped defaults file carries only the SQLite path and the default delivery mode. All authorization is computed live from Mattermost's role API + the per-channel SQLite allowlist.

## Delivery semantics

Three modes. **Default is `dm`** — chosen for the rules-of-server use case where force-pushing the rules to the joiner matters more than publicly acknowledging the arrival.

- **`dm`** *(default)* — bot creates a direct channel with the user via `POST /api/v4/channels/direct`, posts the full message there. Mattermost surfaces DMs prominently with a badge and (if user has push notifs enabled) a system notification. Hard to miss.
- **`channel`** — bot posts the welcome in the channel itself, mentioning `@user` if the message contains `{user}`. Social-pressure mode. Visible to everyone but easy to miss in busy channels.
- **`both`** — short `public_greet` line in the channel ("Welcome @user — DM'd you the rules"), full message in DM. Use when both social acknowledgement and force-push delivery matter.

## Message templating

Support exactly one placeholder for v1: `{user}` → expands to `@username`. Anything else (channel name, join date, custom variables) deferred until someone asks for it. Keeps the v1 parser trivial.

## What survives bot restart

- `welcome_configs` — all welcome rules.
- `welcomed_users` — all sightings, so re-joins are not re-welcomed.
- The reconcile-on-startup pass catches users who joined while the bot was offline.

## What it does NOT try to do (deliberately)

- No multi-message welcomes (one message per channel; admins use markdown for length).
- No per-user welcome (the rules are channel rules, not user-specific).
- No expiry / re-welcome after N days (could add later via timestamp + TTL on `welcomed_users`).
- No emoji-reaction acknowledgement flow (interesting follow-up but separate scope).
- No template engine — single placeholder, that's it.
- No automatic channel-admin role detection — explicit admin list. Mattermost's role API is more involved than worth wiring into v1.

## Integration touch on `matterbot.py`

Three small adds:

1. In `handle_post` early-branch: if `post['type'] == 'system_join_channel'`, call `welcome.on_join(post['user_id'], post['channel_id'])` and `return` (don't run command dispatch on system posts).
2. In the WebSocket dispatch (wherever `posted` / `user_added` events arrive): add a case for `user_added` that calls `welcome.on_join(event['data']['user_id'], event['broadcast']['channel_id'])`.
3. In the post-reconnect path (now that PR #153's reconnect loop exists): call `welcome.reconcile()` once per successful reconnect. The reconcile function iterates configured channels and welcomes any user we missed.

Everything else lives in `commands/welcome/`. No spillover into the rest of the bot.

## Failure modes covered

- **Bot offline during join** → reconcile on reconnect catches the joiner.
- **User leaves + rejoins** → already in `welcomed_users`, no re-welcome.
- **Duplicate `posted` + `user_added` events for the same join** → atomic upsert into `welcomed_users` makes the second call a no-op.
- **DM creation fails (Mattermost API hiccup)** → log + don't insert into `welcomed_users`, so next sighting will retry. (Tradeoff: if the API is *permanently* broken for one user, the bot will re-attempt every reconcile cycle. Add a `failed_attempts` counter later if it becomes noisy.)
- **Welcome configured for a now-deleted channel** → reconcile finds the channel returns 404, logs once, marks config as disabled.
- **Channel renamed** → `channel_id` is stable, transparent.

## Test plan

- `@welcome set Welcome! Rules: be kind.` in `#test-channel` (run by a `system_admin` or a `channel_admin` of `#test-channel`) → config stored, existing members silently marked welcomed.
- Non-admin runs `@welcome set` → polite refusal in the same channel, no state change, no welcome-config written.
- New user joins `#test-channel` → bot DMs them within seconds (default delivery `dm`). `welcomed_users` row inserted.
- Same user re-joins after leaving → no DM. `welcomed_at` unchanged.
- Bot restart → state intact, no re-welcome of anyone in `welcomed_users`.
- Bot offline → user joins → bot restarts → reconcile pass DMs the user.
- Two channels with different welcome configs, same user joins both → two DMs (one per channel), each with the right channel's rules.
- `@welcome delivery both` + `@welcome greet "Welcome {user}!"` → next joiner gets a public greet AND a DM.
- `@welcome admin add @alice` (run by a `system_admin` or `channel_admin`) → Alice can now run any `@welcome` subcommand in this channel. Same call from Alice WITHOUT prior privileges → refusal.
- `@welcome admin remove @alice` → Alice can no longer configure welcome in this channel.
- `@welcome admin list` → shows the per-channel allowlist.
- System admin runs `@welcome set` in a channel they are NOT a member of → succeeds (system_admin bypasses the channel-member check).

## Resolved decisions

- **Storage location** — `commands/welcome/state.db`, lives next to `command.py` / `defaults.py` in the module directory.
- **Default delivery mode** — `dm`. Configurable per-channel via `@welcome delivery channel|both`.
- **Admin model** — three-source auth (`system_admin` Mattermost role OR `channel_admin` Mattermost role for the target channel OR explicit per-channel allowlist in the `channel_admins` table). The allowlist is managed at runtime via `@welcome admin add/remove/list`. `defaults.py` ships no static admin list; all authorization is computed live.
