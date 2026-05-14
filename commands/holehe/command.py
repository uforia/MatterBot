#!/usr/bin/env python3

import logging
import re
import shutil
import subprocess

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

# Strict RFC-5321-ish local + RFC-1123 domain. Rejects whitespace, quotes, and
# shell metacharacters so the operator-supplied string is safe to pass as a
# positional arg to the holehe binary.
_EMAIL_RE = re.compile(
    r"^(?=.{1,254}$)"
    r"[A-Za-z0-9!#$%&'*+\-/=?^_`{|}~.]{1,64}"
    r"@"
    r"(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)

# Holehe's `--only-used` output is one service per line as `[+] <service>`.
# Anchor at start-of-line to avoid picking up banner text or summary rows.
_HIT_RE = re.compile(r"^\s*\[\+\]\s+(\S+)\s*$")

# Summary footer line, e.g. "[~] 5 found, 27 not found, 5 errors, 91 disabled,
# 0 rate limited, 128 total". We surface this verbatim if present so the user
# knows how many services were skipped or rate-limited.
_SUMMARY_RE = re.compile(r"^\s*\[~\]\s+(.*found.*)$")


def _format_results(email, hits, summary):
    if not hits:
        body = f"No services report `{email}` as registered."
    else:
        lines = [f"## Registered services ({len(hits)})"]
        for service in hits:
            lines.append(f"  {service}")
        body = "\n".join(lines)
    if summary:
        body += f"\n\n_{summary}_"
    return body


def process(command, channel, username, params, files, conn):
    messages = []

    if not params:
        return {
            "messages": [
                {
                    "text": "Usage: `@holehe <email>` — checks if an email is "
                    "registered against ~120 online services."
                }
            ]
        }

    email = params[0].strip()
    if not _EMAIL_RE.match(email):
        return {
            "messages": [
                {
                    "text": f"`{params[0]}` does not look like a valid email "
                    "address. Pass a bare address like `user@example.com`."
                }
            ]
        }

    holehe_path = shutil.which("holehe")
    if not holehe_path:
        log.warning(
            "holehe module: holehe binary not on PATH; "
            "install with `pip install holehe`"
        )
        return {
            "messages": [
                {
                    "text": "Holehe is not installed on this host. "
                    "Run `pip install holehe` and restart the bot."
                }
            ]
        }

    try:
        completed = subprocess.run(
            [holehe_path, "--no-color", "--only-used", email],
            capture_output=True,
            text=True,
            timeout=settings.TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        log.warning("holehe module: timed out after %ss", settings.TIMEOUT)
        return {
            "messages": [
                {
                    "text": f"Holehe timed out after {settings.TIMEOUT}s. "
                    "Try again later or raise TIMEOUT in settings."
                }
            ]
        }
    except Exception as e:
        log.exception("holehe module: subprocess failure")
        return {
            "messages": [{"text": f"An error occurred in Holehe:\nError: {str(e)}"}]
        }

    hits = []
    summary = ""
    for line in completed.stdout.splitlines():
        m = _HIT_RE.match(line)
        if m:
            hits.append(m.group(1))
            continue
        m = _SUMMARY_RE.match(line)
        if m:
            summary = m.group(1).strip()

    body = _format_results(email, hits, summary)

    truncated = False
    if len(body) > settings.MAX_OUTPUT_CHARS:
        body = body[: settings.MAX_OUTPUT_CHARS]
        truncated = True

    wrapped = f"**Holehe results for `{email}`:**\n```\n{body}\n```"
    if truncated:
        wrapped += (
            f"\n_Output truncated at {settings.MAX_OUTPUT_CHARS} characters._"
        )

    messages.append({"text": wrapped})
    return {"messages": messages}
