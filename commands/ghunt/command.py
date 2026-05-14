#!/usr/bin/env python3

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

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

# Strict RFC-5321-ish local + RFC-1123 domain. Rejects whitespace, quotes and
# shell metacharacters so the operator-supplied string is safe to pass as a
# positional arg to ghunt.
_EMAIL_RE = re.compile(
    r"^(?=.{1,254}$)"
    r"[A-Za-z0-9!#$%&'*+\-/=?^_`{|}~.]{1,64}"
    r"@"
    r"(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)

# Markers in ghunt's stderr/stdout that indicate the operator never ran
# `ghunt login` (or that the persisted cookie expired). Surfacing this as a
# distinct error makes the failure mode obvious to the user.
_AUTH_FAIL_HINTS = (
    "no credentials",
    "authentication failed",
    "please login",
    "creds.m",
    "not authenticated",
)


def _summarize_profile(data):
    # Ghunt's JSON schema is large and evolves between releases; we surface a
    # stable subset (PROFILE_CONTAINER + service hits) instead of dumping the
    # whole payload — channel readers want a triage view, not the full tree.
    if not isinstance(data, dict):
        return "Ghunt returned an unexpected JSON shape."

    profile = data.get("PROFILE_CONTAINER", {}).get("profile", {}) or {}
    services = data.get("PROFILE_CONTAINER", {}).get("services", {}) or {}

    name = profile.get("names", {}).get("full_name") or profile.get("name") or "?"
    gaia_id = profile.get("gaia_id") or "?"
    profile_url = profile.get("profile_url") or ""

    lines = [
        f"Name:        {name}",
        f"Gaia ID:     {gaia_id}",
    ]
    if profile_url:
        lines.append(f"Profile URL: {profile_url}")

    enabled = sorted(
        svc for svc, blob in services.items() if isinstance(blob, dict) and blob
    )
    if enabled:
        lines.append("")
        lines.append(f"Services with data ({len(enabled)}):")
        for svc in enabled:
            lines.append(f"  - {svc}")

    reviews = data.get("PUBLIC_PROFILE_CONTAINER", {}).get("reviews", []) or []
    if reviews:
        lines.append("")
        lines.append(f"Public Maps reviews: {len(reviews)}")

    return "\n".join(lines)


def _detect_auth_failure(stderr_text):
    lowered = stderr_text.lower()
    return any(hint in lowered for hint in _AUTH_FAIL_HINTS)


def process(command, channel, username, params, files, conn):
    messages = []

    if not params:
        return {
            "messages": [
                {
                    "text": "Usage: `@ghunt <email>` — looks up a Google "
                    "account by email and returns the public profile data."
                }
            ]
        }

    email = params[0].strip()
    if not _EMAIL_RE.match(email):
        return {
            "messages": [
                {
                    "text": f"`{params[0]}` does not look like a valid email "
                    "address. Pass a bare address like `user@gmail.com`."
                }
            ]
        }

    ghunt_path = shutil.which("ghunt")
    if not ghunt_path:
        log.warning(
            "ghunt module: ghunt binary not on PATH; install with `pip install ghunt` "
            "(Python <=3.11 only — ghunt pins pillow==9.3.0 which does not build on 3.12+)"
        )
        return {
            "messages": [
                {
                    "text": "Ghunt is not installed on this host. Run "
                    "`pip install ghunt` (requires Python ≤3.11 — ghunt pins "
                    "`pillow==9.3.0`, which does not build on 3.12+), then "
                    "`ghunt login`, then restart the bot."
                }
            ]
        }

    # NamedTemporaryFile with delete=False so we can close the handle before
    # ghunt writes to it (Windows would otherwise refuse, and on POSIX it
    # keeps the file descriptor count flat). We explicitly remove it in the
    # finally block.
    tmp = tempfile.NamedTemporaryFile(
        prefix="ghunt-",
        suffix=".json",
        delete=False,
    )
    tmp_path = tmp.name
    tmp.close()

    try:
        try:
            completed = subprocess.run(
                [ghunt_path, settings.SUBCOMMAND, "--json", tmp_path, email],
                capture_output=True,
                text=True,
                timeout=settings.TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired:
            log.warning("ghunt module: timed out after %ss", settings.TIMEOUT)
            return {
                "messages": [
                    {
                        "text": f"Ghunt timed out after {settings.TIMEOUT}s. "
                        "Try again later or raise TIMEOUT in settings."
                    }
                ]
            }
        except Exception as e:
            log.exception("ghunt module: subprocess failure")
            return {
                "messages": [
                    {"text": f"An error occurred in Ghunt:\nError: {str(e)}"}
                ]
            }

        if _detect_auth_failure(completed.stderr) or _detect_auth_failure(
            completed.stdout
        ):
            log.warning("ghunt module: authentication failure")
            return {
                "messages": [
                    {
                        "text": "Ghunt is not authenticated. The bot host operator "
                        "must run `ghunt login` (interactive) and re-run the command."
                    }
                ]
            }

        try:
            with open(tmp_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            # Either ghunt did not write a JSON file at all, or it wrote something
            # malformed. In either case the stderr will normally carry the actual
            # reason; surface the first stderr line so the user has something
            # actionable instead of a generic parse error.
            stderr_first_line = (completed.stderr or "").strip().splitlines()
            hint = stderr_first_line[0] if stderr_first_line else "no output"
            log.warning("ghunt module: no parseable JSON, ghunt stderr: %r", hint)
            return {
                "messages": [
                    {
                        "text": f"Ghunt returned no parseable result for `{email}`. "
                        f"ghunt stderr: `{hint}`"
                    }
                ]
            }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    body = _summarize_profile(data)

    truncated = False
    if len(body) > settings.MAX_OUTPUT_CHARS:
        body = body[: settings.MAX_OUTPUT_CHARS]
        truncated = True

    wrapped = f"**Ghunt profile for `{email}`:**\n```\n{body}\n```"
    if truncated:
        wrapped += (
            f"\n_Output truncated at {settings.MAX_OUTPUT_CHARS} characters._"
        )

    messages.append({"text": wrapped})
    return {"messages": messages}
