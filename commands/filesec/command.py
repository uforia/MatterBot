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

# File extensions: 1-12 chars, alphanumeric only (a few legitimate extensions
# include digits, e.g. mp3, mp4, 7z). Anything outside this character class
# can't legitimately be a file extension and would just produce noise.
EXT_RE = re.compile(r'^[a-zA-Z0-9]{1,12}$')


def _normalize_ext(raw):
    if not raw:
        return None
    q = raw.strip().lstrip('.').lower()
    return q if EXT_RE.match(q) else None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _format(ext, payload, max_refs):
    if not isinstance(payload, dict):
        return None

    rows = [('Extension', f'.{ext}')]
    name = payload.get('name') or payload.get('extension')
    if name and name != ext and name != f'.{ext}':
        rows.append(('Name', name))

    description = payload.get('description') or payload.get('useCases') or payload.get('use_cases')
    # Description is rendered as a quoted block below the table; not a row.

    attributes = payload.get('attributes') or {}
    # Normalise booleans into a compact key=Y/N list so the table row stays
    # readable even when ~10 attribute flags are set.
    if isinstance(attributes, dict) and attributes:
        flags = []
        for k, v in attributes.items():
            if isinstance(v, bool):
                flags.append(f"{k}={'Y' if v else 'N'}")
            elif v is not None and v != '':
                flags.append(f"{k}={_cell(v)}")
        if flags:
            rows.append(('Attributes', ', '.join(flags)))

    last_modified = payload.get('lastModified') or payload.get('last_modified') or payload.get('updated')
    if last_modified:
        rows.append(('Last modified', last_modified))

    lines = [f"FileSec record for `.{ext}`:"]
    if description:
        # Strip down to a single block of prose, keep it manageable.
        desc = ' '.join(str(description).split())
        if len(desc) > 600:
            desc = desc[:599].rstrip() + '…'
        lines.append(f"> {desc}")
        lines.append('')
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    references = payload.get('references') or payload.get('refs') or []
    if isinstance(references, list) and references:
        shown = references[:max_refs]
        lines.append('')
        lines.append('**References:**')
        for r in shown:
            if isinstance(r, dict):
                url = r.get('url') or ''
                title = r.get('title') or ''
                if url:
                    lines.append(f"- [{_cell(title) if title else url}]({url})")
            elif isinstance(r, str):
                lines.append(f"- {r}")
        if len(references) > max_refs:
            lines.append(f"_…{len(references) - max_refs} more reference(s) not shown._")

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@filesec <extension>` (e.g. `@filesec lnk`, `@filesec .iso`)."}]}

    ext = _normalize_ext(params[0])
    if not ext:
        return {'messages': [{'text': f"FileSec: `{_cell(params[0])}` is not a valid file extension."}]}

    cfg = getattr(settings, 'APIURL', {}).get('filesec', {})
    url_pattern = cfg.get('url_pattern') or 'https://filesec.io/api/v1/extensions/{ext}'
    max_refs = int(getattr(settings, 'MAX_REFERENCES', 6))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    # Use string substitution rather than format() to avoid an unintended
    # keyword conflict if the URL pattern ever includes other braces.
    url = url_pattern.replace('{ext}', requests.utils.quote(ext, safe=''))

    try:
        resp = requests.get(
            url,
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot FileSec module',
            },
            allow_redirects=True,    # filesec.io may serve the JSON from a CDN that redirects
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("filesec request failed")
        return {'messages': [{'text': f"FileSec request failed: `{e}`"}]}

    if resp.status_code == 404:
        return {'messages': [{'text': f"FileSec: `.{ext}` is not tracked on filesec.io."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"FileSec returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("filesec returned non-JSON")
        return {'messages': [{'text': 'FileSec returned a non-JSON response. The URL pattern in `settings.py` may be out of date.'}]}

    text = _format(ext, payload, max_refs)
    if not text:
        return {'messages': [{'text': f"FileSec: unrecognised response shape for `.{ext}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
