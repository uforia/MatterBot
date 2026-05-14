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

# Search term: 1-200 printable chars, reject control chars.
QUERY_RE = re.compile(r'^[^\x00-\x1f\x7f]{1,200}$')
# Comma-separated platform list. Whitelist commonly-supported sites; reject
# anything outside it.
ALLOWED_SITES = {
    'telegram', 'bitchute', 'gab', 'gettr', 'parler', 'minds', 'truth_social',
    '4chan', 'poal', 'win', 'rumble', 'mewe', 'rutube',
}


def _normalize_query(raw):
    if not raw:
        return None
    q = raw.strip()
    if not q:
        return None
    return q if QUERY_RE.match(q) else None


def _normalize_sites(raw):
    if not raw:
        return None
    parts = [p.strip().lower() for p in raw.split(',') if p.strip()]
    clean = [p for p in parts if p in ALLOWED_SITES]
    return ','.join(clean) if clean else None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim(value, n):
    s = str(value or '')
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _format(query, sites, payload, max_results):
    # Open Measures returns either:
    #   {hits: {total: N, hits: [...]}}
    #   {results: [...], total: N}
    #   [...] (top-level list, older endpoints)
    hits = []
    total = None
    if isinstance(payload, dict):
        if isinstance(payload.get('hits'), dict):
            inner = payload['hits']
            if isinstance(inner.get('hits'), list):
                hits = inner['hits']
            total = inner.get('total') if isinstance(inner.get('total'), int) else None
        if not hits and isinstance(payload.get('results'), list):
            hits = payload['results']
            total = payload.get('total') if isinstance(payload.get('total'), int) else len(hits)
    elif isinstance(payload, list):
        hits = payload
        total = len(payload)

    if not hits:
        return f"Open Measures: no results for `{_cell(query)}` (sites: `{_cell(sites)}`)."

    if total is None:
        total = len(hits)
    truncated = len(hits) > max_results
    shown = hits[:max_results]

    lines = [f"Open Measures results for `{_cell(query)}` on `{_cell(sites)}` — showing {len(shown)} of {total}:"]
    lines.append('')

    for i, h in enumerate(shown, 1):
        # Each hit may be a {_source: {...}} ES-style envelope or a flat dict.
        source = h.get('_source') if isinstance(h, dict) and isinstance(h.get('_source'), dict) else h
        if not isinstance(source, dict):
            continue
        site = source.get('site') or source.get('platform') or source.get('source') or '?'
        ts = source.get('timestamp') or source.get('published') or source.get('date') or ''
        text = source.get('text') or source.get('content') or source.get('message') or source.get('snippet') or ''
        url = source.get('url') or source.get('link') or source.get('permalink') or ''
        # Defang URLs to avoid auto-linking known-fringe domains in-channel.
        url = url.replace('http://', 'hxxp://').replace('https://', 'hxxps://') if isinstance(url, str) else ''

        lines.append(f"**{i}. `{_cell(site)}`** · `{_cell(ts)}`")
        if text:
            # Wrap in inline-code so upstream post text can't inject
            # @-mentions or markdown links via the blockquote.
            lines.append(f"> `{_trim(_cell(text), 300)}`")
        if url:
            lines.append(f"  ↳ {url}")
        lines.append('')

    if truncated:
        lines.append(f"_…{total - max_results} more hit(s) not shown._")

    return '\n'.join(lines).rstrip()


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@openmeasures <search term>`."}]}

    raw = ' '.join(params)
    query = _normalize_query(raw)
    if not query:
        return {'messages': [{'text': "Open Measures: query rejected (1-200 printable chars)."}]}

    cfg = getattr(settings, 'APIURL', {}).get('openmeasures', {})
    base = (cfg.get('url') or '').rstrip('/') + '/'
    key = cfg.get('key') or ''
    sites_raw = getattr(settings, 'DEFAULT_SITES', 'telegram,bitchute,gab,gettr')
    sites = _normalize_sites(sites_raw) or 'telegram'
    max_results = int(getattr(settings, 'MAX_RESULTS', 8))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    headers = {
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot Open Measures module',
    }
    if key and not key.startswith('<'):
        headers['X-API-KEY'] = key

    url = base + 'content'
    try:
        resp = requests.get(
            url,
            params={'term': query, 'site': sites, 'limit': max_results},
            headers=headers,
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("openmeasures request failed")
        return {'messages': [{'text': f"Open Measures request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Open Measures: authentication failed — clear `key` for free tier or set a valid paid key.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'Open Measures: rate-limited (HTTP 429). Free tier is ~39 req/day per source IP.'}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Open Measures returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("openmeasures returned non-JSON")
        return {'messages': [{'text': 'Open Measures returned a non-JSON response.'}]}

    text = _format(query, sites, payload, max_results)
    if not text:
        return {'messages': [{'text': f"Open Measures: unrecognised response shape for `{_cell(query)}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
