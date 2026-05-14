#!/usr/bin/env python3

import logging
import re

import requests

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

# Hex-only hash shapes. Anchored to prevent operator-supplied junk from
# being passed as `search_term` — yaraify echoes the term in error
# responses, so a clean validator keeps the JSON body well-formed.
_HASH_RE = {
    "md5": re.compile(r"^[A-Fa-f0-9]{32}$"),
    "sha1": re.compile(r"^[A-Fa-f0-9]{40}$"),
    "sha256": re.compile(r"^[A-Fa-f0-9]{64}$"),
}


def _classify_hash(value):
    for kind, rx in _HASH_RE.items():
        if rx.match(value):
            return kind
    return None


def _format_sample(sample):
    """Format a single sample-record into a single line + indented rules block."""
    sha256 = sample.get("sha256_hash") or "?"
    signature = sample.get("signature") or "Unknown"
    file_name = sample.get("file_name") or ""
    file_type = sample.get("file_type") or ""
    first_seen = sample.get("first_seen") or ""
    tags = sample.get("tags") or []
    yara_rules = sample.get("yara_rules") or []

    parts = [f"- **{signature}** `{sha256}`"]
    if file_name:
        parts.append(f"name=`{file_name}`")
    if file_type:
        parts.append(f"type=`{file_type}`")
    if first_seen:
        parts.append(f"first_seen=`{first_seen}`")
    if tags:
        parts.append("tags=`" + "`, `".join(tags) + "`")
    header = " | ".join(parts)

    if not yara_rules:
        return header

    # yara_rules is a list of dicts with keys like rule_name, author,
    # description. Surface just rule_name as a triage line — channel readers
    # can pivot from there to yaraify.abuse.ch for the full match detail.
    rule_lines = []
    for r in yara_rules[: settings.MAX_RULES]:
        if isinstance(r, dict):
            name = r.get("rule_name") or r.get("name") or "?"
        else:
            name = str(r)
        rule_lines.append(f"  - {name}")
    if len(yara_rules) > settings.MAX_RULES:
        rule_lines.append(
            f"  _… {len(yara_rules) - settings.MAX_RULES} more rule(s); see yaraify.abuse.ch for the full set._"
        )

    return header + "\n  Matched YARA rules (" + str(len(yara_rules)) + "):\n" + "\n".join(rule_lines)


def process(command, channel, username, params, files, conn):
    if not params:
        return {
            "messages": [
                {
                    "text": "Usage: `@yaraify <MD5|SHA1|SHA256>` — looks up a "
                    "file hash on abuse.ch Yaraify and reports matched YARA rules."
                }
            ]
        }

    raw = params[0].strip()
    hash_kind = _classify_hash(raw)
    if not hash_kind:
        return {
            "messages": [
                {
                    "text": f"`{params[0]}` does not look like an MD5/SHA1/SHA256 "
                    "hex hash. Pass a 32/40/64-character hexadecimal string."
                }
            ]
        }

    headers = {"Content-Type": settings.CONTENTTYPE}
    auth_key = settings.APIURL["yaraify"].get("key") or ""
    if auth_key:
        headers["Auth-Key"] = auth_key

    body = {"query": "lookup_hash", "search_term": raw}

    try:
        response = requests.post(
            settings.APIURL["yaraify"]["url"],
            json=body,
            headers=headers,
            timeout=(10, settings.TIMEOUT),
            allow_redirects=False,
        )
    except requests.exceptions.Timeout:
        log.warning("yaraify: request timed out after %ss", settings.TIMEOUT)
        return {
            "messages": [
                {
                    "text": f"Yaraify request timed out after {settings.TIMEOUT}s. "
                    "Try again later."
                }
            ]
        }
    except requests.exceptions.RequestException:
        log.exception("yaraify: request failed")
        return {
            "messages": [
                {"text": "Yaraify request failed. Check bot logs for details."}
            ]
        }

    if response.status_code != 200:
        log.warning("yaraify: HTTP %s for %s", response.status_code, raw)
        return {
            "messages": [
                {
                    "text": f"Yaraify returned HTTP {response.status_code} for "
                    f"`{raw}`."
                }
            ]
        }

    try:
        data = response.json()
    except ValueError:
        log.exception("yaraify: non-JSON response")
        return {
            "messages": [
                {"text": "Yaraify returned a malformed response body."}
            ]
        }

    status = data.get("query_status")
    if status == "no_results":
        return {
            "messages": [
                {"text": f"Yaraify has no record for `{raw}` ({hash_kind})."}
            ]
        }
    if status == "illegal_search_term":
        return {
            "messages": [
                {"text": f"Yaraify rejected `{raw}` as an invalid search term."}
            ]
        }
    if status != "ok":
        # Includes "http_post_expected", "illegal_hash", "missing_hash",
        # and any future status strings — surface verbatim so the operator
        # can diagnose without reading bot logs.
        return {
            "messages": [
                {"text": f"Yaraify query_status=`{status}` for `{raw}`."}
            ]
        }

    samples = data.get("data") or []
    if not samples:
        return {
            "messages": [
                {"text": f"Yaraify returned status=ok but no samples for `{raw}`."}
            ]
        }

    parts = [f"**Yaraify results for `{raw}` ({hash_kind}):**"]
    for sample in samples:
        parts.append(_format_sample(sample))
    body_text = "\n".join(parts)

    truncated = False
    if len(body_text) > settings.MAX_OUTPUT_CHARS:
        body_text = body_text[: settings.MAX_OUTPUT_CHARS]
        truncated = True
    if truncated:
        body_text += (
            f"\n_Output truncated at {settings.MAX_OUTPUT_CHARS} characters; "
            "see yaraify.abuse.ch for the full result._"
        )

    return {"messages": [{"text": body_text}]}
