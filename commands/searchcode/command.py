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

# Reject pathological inputs — newlines, control chars, and queries longer
# than 250 chars. Searchcode otherwise accepts pretty arbitrary text.
QUERY_RE = re.compile(r'^[^\x00-\x1f\x7f]{1,250}$')


def _normalize_query(raw):
    if not raw:
        return None
    q = raw.strip()
    if not q:
        return None
    return q if QUERY_RE.match(q) else None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _format(query, payload, max_results, max_snippet):
    if not isinstance(payload, dict):
        return None
    results = payload.get('results') or []
    total = payload.get('total') if isinstance(payload.get('total'), int) else len(results)

    if not results:
        return f"Searchcode: no results for `{_cell(query)}`."

    truncated = len(results) > max_results
    shown = results[:max_results]

    lines = [f"Searchcode results for `{_cell(query)}` — showing {len(shown)} of ~{total}:"]
    lines.append('')

    for i, r in enumerate(shown, 1):
        if not isinstance(r, dict):
            continue
        repo = r.get('repo') or '?'
        filename = r.get('filename') or '?'
        language = r.get('language') or '?'
        lines_data = r.get('lines') or {}
        url = r.get('url') or ''

        lines.append(f"**{i}. `{_cell(filename)}`** · `{_cell(language)}` · [{_cell(repo)}]({_cell(url)})")

        # `lines` is a dict {line_number_str: code_line}. Render the first
        # MAX-SNIPPET-CHARS-worth.
        if isinstance(lines_data, dict) and lines_data:
            snippet_lines = []
            char_budget = max_snippet
            for ln in sorted(lines_data.keys(), key=lambda s: int(s) if s.isdigit() else 0):
                code = str(lines_data[ln]).rstrip()
                fragment = f"{ln}: {code}"
                if char_budget - len(fragment) < 0:
                    if char_budget > 4:
                        snippet_lines.append(fragment[:char_budget - 1] + '…')
                    break
                snippet_lines.append(fragment)
                char_budget -= len(fragment) + 1
            if snippet_lines:
                lines.append('```')
                lines.extend(snippet_lines)
                lines.append('```')
        lines.append('')

    if truncated:
        lines.append(f"_…{len(results) - max_results} more result(s) on this page not shown._")

    return '\n'.join(lines).rstrip()


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@searchcode <query>` (e.g. `@searchcode AWS_SECRET_ACCESS_KEY`)."}]}

    # Searchcode queries can be multi-token — join all params with space.
    raw = ' '.join(params)
    query = _normalize_query(raw)
    if not query:
        return {'messages': [{'text': "Searchcode: query rejected (must be 1-250 printable chars)."}]}

    cfg = getattr(settings, 'APIURL', {}).get('searchcode', {})
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_results = int(getattr(settings, 'MAX_RESULTS', 8))
    max_snippet = int(getattr(settings, 'MAX_SNIPPET_CHARS', 240))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    url = base + 'codesearch_json/'
    try:
        resp = requests.get(
            url,
            params={'q': query, 'p': 0},
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot Searchcode module',
            },
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("searchcode request failed")
        return {'messages': [{'text': f"Searchcode request failed: `{e}`"}]}

    if resp.status_code == 429:
        return {'messages': [{'text': 'Searchcode: rate-limited (HTTP 429). Try again later.'}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Searchcode returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("searchcode returned non-JSON")
        return {'messages': [{'text': 'Searchcode returned a non-JSON response.'}]}

    text = _format(query, payload, max_results, max_snippet)
    if not text:
        return {'messages': [{'text': f"Searchcode: empty response for `{_cell(query)}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
