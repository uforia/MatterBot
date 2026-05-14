#!/usr/bin/env python3

import datetime
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

MD5_RE = re.compile(r'^[A-Fa-f0-9]{32}$')
SHA1_RE = re.compile(r'^[A-Fa-f0-9]{40}$')
SHA256_RE = re.compile(r'^[A-Fa-f0-9]{64}$')


def _classify_hash(raw):
    if not raw:
        return None, None
    q = raw.strip()
    if MD5_RE.match(q):
        return q.lower(), 'md5'
    if SHA1_RE.match(q):
        return q.lower(), 'sha1'
    if SHA256_RE.match(q):
        return q.lower(), 'sha256'
    return None, None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _fmt_added(value):
    """MalShare returns `added` as a unix timestamp or YYYY-MM-DD HH:MM:SS string."""
    if value is None:
        return None
    try:
        ts = int(value)
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    except (TypeError, ValueError):
        return str(value)


def _format(query_hash, query_kind, payload, max_sources):
    if not isinstance(payload, dict):
        return None

    rows = []
    rows.append(('Query', f"{query_hash} ({query_kind})"))

    md5 = payload.get('md5')
    sha1 = payload.get('sha1')
    sha256 = payload.get('sha256')
    if md5:
        rows.append(('MD5', md5))
    if sha1:
        rows.append(('SHA1', sha1))
    if sha256:
        rows.append(('SHA256', sha256))

    ssdeep = payload.get('ssdeep')
    if ssdeep:
        rows.append(('ssdeep', ssdeep))

    f_type = payload.get('f_type') or payload.get('FILETYPE') or payload.get('type')
    if f_type:
        rows.append(('File type', f_type))

    added = _fmt_added(payload.get('added') or payload.get('timestamp'))
    if added:
        rows.append(('First seen', added))

    if not rows or len(rows) == 1:
        # Only `Query` row — no real data came back.
        return None

    lines = [f"MalShare record for `{query_hash}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    # Top-pick reference uses SHA256 if available, otherwise the queried hash.
    ref_hash = sha256 or query_hash
    lines.append(f"| Reference | [MalShare sample](https://malshare.com/sample.php?action=detail&hash={ref_hash}) |")

    # Sources — MalShare returns these as a list of URL strings, sometimes
    # under `sources` (plural) or `source` (singular).
    sources = payload.get('sources')
    if not sources and payload.get('source'):
        s = payload['source']
        sources = s if isinstance(s, list) else [s]
    if isinstance(sources, list) and sources:
        total = len(sources)
        truncated = total > max_sources
        shown = sources[:max_sources]
        lines.append('')
        lines.append(f"**Sources ({len(shown)} of {total}):**")
        for s in shown:
            if not isinstance(s, str):
                continue
            # Defang URLs so the channel renderer doesn't auto-link known-bad
            # destinations.
            defanged = s.replace('http', 'hxxp').replace('.', '[.]', 1) if s.startswith(('http', 'hxxp')) else s
            lines.append(f"- `{_cell(defanged)}`")
        if truncated:
            lines.append(f"_…{total - max_sources} more source(s) not shown._")

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    raw = params[0]
    query_hash, query_kind = _classify_hash(raw)
    if not query_hash:
        # Silent no-op on shape mismatch (matches @ioc convention).
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('malshare', {})
    key = cfg.get('key') or ''
    base = cfg.get('url') or 'https://malshare.com/api.php'
    max_sources = int(getattr(settings, 'MAX_SOURCES', 10))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'MalShare is not configured. Set `key` in `settings.py` (free registration at https://malshare.com/).'}]}

    try:
        resp = requests.get(
            base,
            params={'api_key': key, 'action': 'details', 'hash': query_hash},
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot MalShare module',
            },
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        # Note: api_key is in the query string. Don't echo the URL.
        log.exception("malshare request failed")
        return {'messages': [{'text': f"MalShare request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'MalShare: authentication failed — check API key.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'MalShare: rate-limited (HTTP 429). Daily quota may be exhausted.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"MalShare: no sample matching `{query_hash}`."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"MalShare returned HTTP {resp.status_code}."}]}

    body = resp.text.strip()
    # MalShare returns either JSON object on hit, or a plain error string like
    # `Sample not found by hash` on miss.
    if not body:
        return {'messages': [{'text': f"MalShare: no sample matching `{query_hash}`."}]}
    try:
        payload = resp.json()
    except ValueError:
        # Plain-text error path — surface the message.
        return {'messages': [{'text': f"MalShare: {_cell(body[:300])}"}]}

    text = _format(query_hash, query_kind, payload, max_sources)
    if not text:
        return {'messages': [{'text': f"MalShare: no record for `{query_hash}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
