# Running MatterBot as a supervised service

One dedicated unprivileged account runs both processes. The bot is
sandboxed but the code tree is **not** made read-only — there is no
chat-triggered code path. Code updates are a plain `git pull` on the
host (then `@reload` for command modules); `@restart` only bounces the
already-on-disk code.

## Accounts & layout

```
sudo useradd --system --no-create-home --shell /usr/sbin/nologin matterbot
sudo install -d -o matterbot -g matterbot /var/lib/matterbot
sudo git clone <repo> /opt/matterbot
sudo chown -R matterbot:matterbot /opt/matterbot
sudo -u matterbot python3 -m venv /opt/matterbot/.venv
sudo -u matterbot /opt/matterbot/.venv/bin/pip install -r /opt/matterbot/requirements.txt
```

## config.yaml

Set absolute, writable paths so logs/state live outside the code tree:

- `bindmap: /var/lib/matterbot/bindmap.json`
- `feedmap: /var/lib/matterbot/feedmap.json` (and `Modules.feedmap` to
  the same path until the deprecated alias is removed)
- `logfile: "-"` (logs to stdout → journald)
- Add the Mattermost ids/role names that may `@restart` to
  `Matterbot.botoperators`.

## Enable

```
sudo cp contrib/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now matterbot.service matterfeed.service
journalctl -u matterbot -f
```

## Behaviour

`@restart` (operator-gated) cleanly exits; `Restart=always` relaunches
on the on-disk code, and the bot posts `Back up. ✅` to the originating
thread. `StartLimitBurst` stops a crash-loop after 5 restarts / 300s —
recovery is then manual on the host. On a non-systemd host
(`service_manager: none`, or run from a shell) `@restart` re-execs the
process instead of relying on a supervisor.
