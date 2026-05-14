#!/usr/bin/env python3

import re
import requests
from requests.auth import HTTPBasicAuth

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

# Reject bare hex hashes (MD5/SHA1/SHA256) so an `@ioc <hash>` fan-out doesn't
# burn ChainAbuse quota on inputs that can't possibly be crypto addresses.
HASH_BARE_RE = re.compile(r'^(?:[A-Fa-f0-9]{32}|[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})$')
# ETH-style: 0x + 40 hex (case-insensitive). Normalise to lowercase on the way
# out because the API doesn't honour EIP-55 checksum casing for queries anyway.
ETH_ADDR_RE = re.compile(r'^0x[a-fA-F0-9]{40}$')
# Catch-all for BTC, SOL, TRX, LTC, DOGE, etc. — strict alnum, 26-62 chars.
GENERIC_ADDR_RE = re.compile(r'^[a-zA-Z0-9]{26,62}$')


def _normalize_addr(raw):
    if not raw:
        return None
    q = raw.strip()
    if HASH_BARE_RE.match(q):
        return None  # bare hex hash — definitely not a crypto address
    if ETH_ADDR_RE.match(q):
        return q.lower()
    if GENERIC_ADDR_RE.match(q):
        return q
    return None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim_desc(text, cap):
    if not text:
        return ''
    text = str(text).strip()
    if len(text) <= cap:
        return text
    return text[:cap - 1].rstrip() + '…'


def _format(addr, payload, max_reports, max_desc):
    """Render the /v0/reports paginated response."""
    if not isinstance(payload, dict):
        return None
    count = payload.get('count')
    results = payload.get('results') or []
    if count is None and isinstance(results, list):
        count = len(results)

    if not count:
        return f"ChainAbuse: no reports found for `{addr}`."

    # Tally categories across all results returned on this page.
    categories = {}
    chains = set()
    for r in results:
        if not isinstance(r, dict):
            continue
        cat = r.get('scamCategory') or r.get('category') or 'unknown'
        categories[cat] = categories.get(cat, 0) + 1
        for a in r.get('addresses') or []:
            if isinstance(a, dict) and a.get('chain'):
                chains.add(a['chain'])

    lines = [f"ChainAbuse reports for `{addr}` — **{count}** report{'s' if count != 1 else ''}{' on page' if count > len(results) else ''}:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    if categories:
        ranked = sorted(categories.items(), key=lambda kv: kv[1], reverse=True)
        cat_str = ', '.join(f"{k} ({v})" for k, v in ranked[:10])
        lines.append(f"| **Categories** | `{_cell(cat_str)}` |")
    if chains:
        lines.append(f"| **Chains** | `{_cell(', '.join(sorted(chains)))}` |")
    lines.append(f"| Reference | [ChainAbuse address page](https://www.chainabuse.com/address/{addr}) |")

    if results:
        lines.append('')
        lines.append(f"**Recent reports (first {min(len(results), max_reports)}):**")
        for r in results[:max_reports]:
            if not isinstance(r, dict):
                continue
            cat = r.get('scamCategory') or r.get('category') or 'unknown'
            created = r.get('createdAt') or r.get('created_at') or ''
            desc = _trim_desc(r.get('description'), max_desc)
            line = f"- `{_cell(cat)}`"
            if created:
                line += f" · `{_cell(created)}`"
            if desc:
                line += f" — {_cell(desc)}"
            lines.append(line)

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    raw = params[0]
    addr = _normalize_addr(raw)
    if not addr:
        # Silent no-op on shape mismatch (matches other TI modules under @ioc).
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('chainabuse', {})
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_reports = int(getattr(settings, 'MAX_REPORTS', 5))
    max_desc = int(getattr(settings, 'MAX_DESC_CHARS', 300))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'ChainAbuse is not configured. Set `key` in `settings.py` (free registration at https://www.chainabuse.com/).'}]}

    url = base + 'reports'
    try:
        resp = requests.get(
            url,
            params={'address': addr, 'perPage': max(max_reports, 5)},
            auth=HTTPBasicAuth(key, ''),
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot ChainAbuse module',
            },
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("chainabuse request failed")
        return {'messages': [{'text': f"ChainAbuse request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'ChainAbuse: authentication failed — check API key.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'ChainAbuse: rate-limited (HTTP 429). Try again later.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"ChainAbuse: no reports found for `{addr}`."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"ChainAbuse returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("chainabuse returned non-JSON")
        return {'messages': [{'text': 'ChainAbuse returned a non-JSON response.'}]}

    text = _format(addr, payload, max_reports, max_desc)
    if not text:
        return {'messages': [{'text': f"ChainAbuse: unrecognised response shape for `{addr}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
