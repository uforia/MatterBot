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

# Strict RFC-1123 hostname check — rejects wildcards, paths, IP addresses,
# and shell metacharacters so the operator-supplied string is safe to
# interpolate into the PhishStats `_where` filter expression.
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)


def _format_hits(domain, hits):
    if not hits:
        return f"No PhishStats reports for `{domain}`."

    lines = [f"**PhishStats reports for `{domain}` ({len(hits)} most recent):**"]
    for h in hits:
        date = h.get("date") or h.get("date_added") or "?"
        url = h.get("url") or "?"
        score = h.get("score")
        title = (h.get("title") or "").strip()
        country = h.get("countrycode") or h.get("country_code") or ""

        # Defang URL display so the channel renderer doesn't auto-link or
        # preview a known phishing destination — replace the scheme.
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            url = url.replace("http", "hxxp", 1)

        parts = [f"`{date}`", f"`{url}`"]
        if score is not None:
            parts.append(f"score=`{score}`")
        if country:
            parts.append(f"cc=`{country}`")
        if title:
            # Trim ultra-long titles — phishing pages occasionally spam
            # thousands of zero-width chars into <title>.
            t = title[:160] + "…" if len(title) > 160 else title
            parts.append(f"title=`{t}`")
        lines.append("- " + " | ".join(parts))

    return "\n".join(lines)


def process(command, channel, username, params, files, conn):
    if not params:
        return {
            "messages": [
                {
                    "text": "Usage: `@phishstats <domain>` — searches PhishStats "
                    "for recent phishing reports matching the domain or "
                    "hostname substring."
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

    # PhishStats `_where` uses a SQL-like grammar; `*` is the wildcard.
    # We've already pinned `domain` to a strict RFC-1123 shape (no quotes,
    # no parens, no commas), so embedding it directly in the LIKE clause
    # is safe — requests will URL-encode the final querystring.
    params_qs = {
        "_where": f"(host,like,*{domain}*)",
        "_sort": "-date",
        "_size": settings.MAX_RESULTS,
    }

    try:
        response = requests.get(
            settings.APIURL,
            params=params_qs,
            headers={"User-Agent": settings.USER_AGENT},
            timeout=(10, settings.TIMEOUT),
            allow_redirects=False,
        )
    except requests.exceptions.Timeout:
        log.warning("phishstats: timeout after %ss", settings.TIMEOUT)
        return {
            "messages": [
                {
                    "text": f"PhishStats request timed out after {settings.TIMEOUT}s. "
                    "Try again later."
                }
            ]
        }
    except requests.exceptions.RequestException:
        log.exception("phishstats: request failed")
        return {
            "messages": [
                {"text": "PhishStats request failed. Check bot logs for details."}
            ]
        }

    if response.status_code != 200:
        log.warning(
            "phishstats: HTTP %s for %s", response.status_code, domain
        )
        return {
            "messages": [
                {
                    "text": f"PhishStats returned HTTP {response.status_code} "
                    f"for `{domain}`."
                }
            ]
        }

    try:
        hits = response.json()
    except ValueError:
        log.exception("phishstats: non-JSON response")
        return {
            "messages": [
                {"text": "PhishStats returned a malformed response body."}
            ]
        }

    if not isinstance(hits, list):
        log.warning("phishstats: unexpected JSON shape (not a list)")
        return {
            "messages": [
                {"text": "PhishStats returned an unexpected JSON shape."}
            ]
        }

    body = _format_hits(domain, hits)

    truncated = False
    if len(body) > settings.MAX_OUTPUT_CHARS:
        body = body[: settings.MAX_OUTPUT_CHARS]
        truncated = True
    if truncated:
        body += (
            f"\n_Output truncated at {settings.MAX_OUTPUT_CHARS} characters; "
            "see phishstats.info for the full result._"
        )

    return {"messages": [{"text": body}]}
