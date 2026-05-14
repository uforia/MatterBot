#!/usr/bin/env python3

import re
import requests

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
import logging

log = logging.getLogger('MatterBot')
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

# Organisation names can include letters, digits, spaces, ampersand, comma,
# period, hyphen, apostrophe, parens, dash. Cap to 100 chars to avoid
# wasted API calls on pathological inputs.
ORG_RE = re.compile(r"^[a-zA-Z0-9 &,.\-\'()/]{1,100}$")


def _normalize_org(raw):
    if not raw:
        return None
    q = raw.strip()
    if not q:
        return None
    return q if ORG_RE.match(q) else None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _defang(url):
    if not isinstance(url, str):
        return ''
    return url.replace('http://', 'hxxp://').replace('https://', 'hxxps://')


def _extract_hits(payload):
    """Tolerate several response shapes — top-level list, nested under
    `results`, `hits`, or `data`."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ('results', 'hits', 'data', 'items', 'records'):
        v = payload.get(key)
        if isinstance(v, list):
            return v
    return []


def _format(org, payload, max_hits):
    if payload is None:
        return None
    hits = _extract_hits(payload)
    if not hits:
        return f"HIBR: no ransomware listings found for `{_cell(org)}`."

    total = len(hits)
    truncated = total > max_hits
    shown = hits[:max_hits]

    lines = [f"HIBR results for `{_cell(org)}` — {total} listing{'s' if total != 1 else ''}:"]
    lines.append('')
    lines.append('| Operator | Date | Listing URL |')
    lines.append('| :- | :- | :- |')
    for h in shown:
        if not isinstance(h, dict):
            continue
        operator = h.get('operator') or h.get('ransomware') or h.get('group') or h.get('actor') or '?'
        date = h.get('date') or h.get('discovered') or h.get('listed_at') or h.get('first_seen') or ''
        url = h.get('url') or h.get('post_url') or h.get('leak_url') or h.get('reference') or ''
        lines.append(f"| `{_cell(operator)}` | `{_cell(date)}` | `{_cell(_defang(url)) if url else '—'}` |")
    if truncated:
        lines.append(f"_…{total - max_hits} more listing(s) not shown._")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@hibr <organisation name>` (e.g. `@hibr ACME Corp`)."}]}

    raw = ' '.join(params)
    org = _normalize_org(raw)
    if not org:
        return {'messages': [{'text': f"HIBR: `{_cell(raw)}` is not a valid organisation name (must be 1-100 chars; letters, digits, spaces, and `& , . - ' ( ) /` only)."}]}

    cfg = getattr(settings, 'APIURL', {}).get('hibr', {})
    url_pattern = cfg.get('url_pattern') or 'https://api.haveibeenransom.com/v1/search?q={q}'
    key = cfg.get('key') or ''
    max_hits = int(getattr(settings, 'MAX_HITS', 10))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    encoded = requests.utils.quote(org, safe='')
    url = url_pattern.replace('{q}', encoded)

    headers = {
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot HIBR module',
    }
    if key and not key.startswith('<'):
        headers['X-API-KEY'] = key

    try:
        resp = requests.get(
            url,
            headers=headers,
            allow_redirects=True,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("hibr request failed")
        return {'messages': [{'text': f"HIBR request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'HIBR: authentication failed — check `key` or the configured URL.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'HIBR: rate-limited (HTTP 429). Try again later.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"HIBR: no listings found for `{_cell(org)}` (or URL pattern is stale)."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"HIBR returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("hibr returned non-JSON")
        return {'messages': [{'text': 'HIBR returned a non-JSON response. The URL pattern in `settings.py` may need updating.'}]}

    text = _format(org, payload, max_hits)
    if not text:
        return {'messages': [{'text': f"HIBR: unrecognised response shape for `{_cell(org)}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
