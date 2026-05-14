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

# Windows API identifiers are alnum + underscore, max ~64 chars in practice.
# Reject anything outside that class (it can't be a real API name).
API_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]{1,63}$')


def _normalize_api(raw):
    if not raw:
        return None
    q = raw.strip()
    # Allow trailing variant suffix (A/W) — MalAPI usually keys by the bare
    # name though, so we don't strip them automatically; users can pass
    # CreateFileW or CreateFile and either may hit.
    return q if API_RE.match(q) else None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim(value, n):
    s = str(value or '')
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _format(api, payload, max_techniques):
    if not isinstance(payload, dict):
        return None

    rows = [('API', api)]
    library = payload.get('library') or payload.get('dll') or payload.get('module')
    if library:
        rows.append(('Library', library))

    msdn = payload.get('msdn') or payload.get('url') or payload.get('documentation')
    if msdn:
        rows.append(('MSDN', msdn))

    description = payload.get('description')
    if description:
        # Render as quoted prose under the table; not as a row.
        pass

    categories = payload.get('categories') or payload.get('category') or []
    if isinstance(categories, str):
        categories = [categories]
    if isinstance(categories, list) and categories:
        rows.append(('Categories', ', '.join(_cell(c) for c in categories[:max_techniques])))

    lines = [f"MalAPI record for `{_cell(api)}`:"]
    if description:
        desc = ' '.join(str(description).split())
        if len(desc) > 600:
            desc = desc[:599].rstrip() + '…'
        # Wrap the blockquote line in inline-code so an attacker who
        # controls the upstream MalAPI description can't inject @-mentions
        # or markdown links via the blockquote text.
        lines.append(f"> `{_cell(desc)}`")
        lines.append('')
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    # Associated MITRE / tradecraft techniques as a sub-table.
    techniques = (
        payload.get('associatedAttacks')
        or payload.get('attacks')
        or payload.get('techniques')
        or []
    )
    if isinstance(techniques, list) and techniques:
        total = len(techniques)
        shown = techniques[:max_techniques]
        lines.append('')
        lines.append(f"**Associated techniques ({len(shown)} of {total}):**")
        lines.append('| Technique | ID | Notes |')
        lines.append('| :- | :- | :- |')
        for t in shown:
            if isinstance(t, dict):
                name = t.get('name') or t.get('technique') or '?'
                tid = t.get('technique_id') or t.get('id') or ''
                notes = t.get('description') or t.get('notes') or ''
                lines.append(f"| `{_cell(name)}` | `{_cell(tid)}` | `{_cell(_trim(notes, 120))}` |")
            elif isinstance(t, str):
                lines.append(f"| `{_cell(t)}` | — | — |")
        if total > max_techniques:
            lines.append(f"_…{total - max_techniques} more technique(s) not shown._")

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@malapi <Windows API name>` (e.g. `@malapi VirtualAllocEx`)."}]}

    api = _normalize_api(params[0])
    if not api:
        return {'messages': [{'text': f"MalAPI: `{_cell(params[0])}` is not a valid Windows API identifier."}]}

    cfg = getattr(settings, 'APIURL', {}).get('malapi', {})
    url_pattern = cfg.get('url_pattern') or 'https://malapi.io/winapi/{api}'
    max_techniques = int(getattr(settings, 'MAX_TECHNIQUES', 12))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    url = url_pattern.replace('{api}', requests.utils.quote(api, safe=''))

    try:
        resp = requests.get(
            url,
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot MalAPI module',
            },
            allow_redirects=True,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("malapi request failed")
        return {'messages': [{'text': f"MalAPI request failed: `{e}`"}]}

    if resp.status_code == 404:
        return {'messages': [{'text': f"MalAPI: `{api}` is not tracked on malapi.io."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"MalAPI returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("malapi returned non-JSON")
        return {'messages': [{'text': 'MalAPI returned a non-JSON response. The URL pattern in `settings.py` may be out of date.'}]}

    text = _format(api, payload, max_techniques)
    if not text:
        return {'messages': [{'text': f"MalAPI: unrecognised response shape for `{api}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
