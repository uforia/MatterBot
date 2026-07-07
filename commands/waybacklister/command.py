#!/usr/bin/env python3

import logging
import re
from urllib.parse import urlsplit

import requests

from matterbot_formatting import sanitize_block, sanitize_inline

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


def _wrap_output(domain, body, truncation_note):
    """Wrap Wayback output: the enumerated paths go inside a code fence via
    sanitize_block and the domain in inline code via sanitize_inline."""
    return f"**Wayback directory enumeration for `{sanitize_inline(domain)}`:**\n```\n{sanitize_block(body)}\n```{truncation_note}"

# Strict RFC-1123 hostname check — rejects URLs with paths, IPs, and shell
# metacharacters so the operator-supplied string is safe to interpolate into
# the CDX query as a bare host.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)


def _looks_like_directory(url):
    # CDX "original" entries are full URLs. A directory-shaped URL is one whose
    # path component ends in `/` and has no querystring (querystrings on `/`
    # paths almost always mean dynamic endpoints, not file listings).
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.query:
        return False
    path = parts.path or "/"
    return path.endswith("/") and path != "/"


def _format_results(domain, hits, total_rows):
    if not hits:
        return (
            f"No directory-shaped paths found in the Wayback Machine for "
            f"`{domain}` (checked {total_rows} archived URLs)."
        )
    lines = [
        f"## Directory-shaped Wayback paths for {domain} ({len(hits)} of {total_rows} archived URLs)"
    ]
    for url in hits:
        lines.append(f"  {url}")
    return "\n".join(lines)


def process(command, channel, username, params, files, conn):
    messages = []

    if not params:
        return {
            "messages": [
                {
                    "text": "Usage: `@waybacklister <domain>` — enumerates "
                    "archived directory-shaped paths for a domain via the "
                    "Wayback Machine CDX API."
                }
            ]
        }

    raw = params[0].strip().lower().strip(".")
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    domain = raw.split("/", 1)[0]

    if not _DOMAIN_RE.match(domain):
        return {
            "messages": [
                {
                    "text": f"`{params[0]}` does not look like a valid domain. "
                    "Pass a bare hostname like `example.com`."
                }
            ]
        }

    try:
        response = requests.get(
            settings.CDX_URL,
            params={
                "url": f"{domain}/*",
                "output": "json",
                "fl": "original",
                "collapse": "urlkey",
                "limit": settings.CDX_LIMIT,
            },
            headers={"User-Agent": settings.USER_AGENT},
            timeout=(10, settings.TIMEOUT),
            allow_redirects=False,
        )
    except requests.exceptions.Timeout:
        log.warning("waybacklister: CDX timeout for %s", domain)
        return {
            "messages": [
                {
                    "text": f"Wayback CDX timed out after {settings.TIMEOUT}s. "
                    "The Internet Archive is occasionally slow — try again later."
                }
            ]
        }
    except requests.exceptions.RequestException:
        log.exception("waybacklister: CDX request failed")
        return {
            "messages": [
                {
                    "text": "Wayback CDX request failed. "
                    "Check bot logs for details."
                }
            ]
        }

    if response.status_code != 200:
        log.warning(
            "waybacklister: CDX returned HTTP %s for %s",
            response.status_code,
            domain,
        )
        return {
            "messages": [
                {
                    "text": f"Wayback CDX returned HTTP {response.status_code} "
                    f"for `{domain}`."
                }
            ]
        }

    try:
        rows = response.json()
    except ValueError:
        log.exception("waybacklister: CDX returned non-JSON body")
        return {
            "messages": [
                {"text": "Wayback CDX returned a malformed response body."}
            ]
        }

    # CDX json shape: [["original"], ["http://example.com/"], ["http://example.com/about/"], ...]
    # First row is the header; skip it.
    if not rows or len(rows) < 2:
        return {
            "messages": [
                {
                    "text": f"Wayback has no archived URLs for `{domain}`."
                }
            ]
        }

    urls = [row[0] for row in rows[1:] if row]
    hits = sorted({u for u in urls if _looks_like_directory(u)})

    if len(hits) > settings.MAX_RESULTS:
        hits = hits[: settings.MAX_RESULTS]
        truncation_note = (
            f"\n_Result list truncated at {settings.MAX_RESULTS} entries._"
        )
    else:
        truncation_note = ""

    body = _format_results(domain, hits, len(urls))

    truncated = False
    if len(body) > settings.MAX_OUTPUT_CHARS:
        body = body[: settings.MAX_OUTPUT_CHARS]
        truncated = True

    wrapped = _wrap_output(domain, body, truncation_note)
    if truncated:
        wrapped += (
            f"\n_Output truncated at {settings.MAX_OUTPUT_CHARS} characters._"
        )

    messages.append({"text": wrapped})
    return {"messages": messages}
