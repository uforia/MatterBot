"""In-process lifecycle helpers for matterbot @restart.
Pure / injectable I/O only — importable for tests, no Mattermost driver.
"""
import json
import os
import sys
import time
from pathlib import Path

RESTART_MARKER = "restart-marker.json"


def detect_service_manager(options, env=None):
    """'systemd' only if actually running under it (systemd sets
    INVOCATION_ID for every unit). Explicit service_manager: none always
    wins. A config that merely says systemd while run from a shell must
    NOT pretend supervision exists."""
    if env is None:
        env = os.environ
    if str(options.Matterbot.get("service_manager") or "").lower() == "none":
        return "none"
    if env.get("INVOCATION_ID"):
        return "systemd"
    return "none"


def state_dir(options):
    """Writable runtime dir = the directory holding the bindmap (with the
    recommended deployment, /var/lib/matterbot)."""
    bindmap = options.Matterbot.get("bindmap") or "bindmap.json"
    return Path(bindmap).resolve().parent


def write_restart_marker(options, channel_id, root_id):
    (state_dir(options) / RESTART_MARKER).write_text(json.dumps({
        "channel_id": channel_id, "root_id": root_id, "ts": time.time(),
    }))


def read_restart_marker(options):
    p = state_dir(options) / RESTART_MARKER
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except (ValueError, OSError):
        return None


def clear_restart_marker(options):
    (state_dir(options) / RESTART_MARKER).unlink(missing_ok=True)


def self_reexec():
    """Non-systemd fallback for @restart: replace this process image with a
    fresh interpreter on the same argv. Last resort only."""
    os.execv(sys.executable, [sys.executable] + sys.argv)
