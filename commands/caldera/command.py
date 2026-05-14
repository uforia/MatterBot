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

# Caldera identifiers (adversary/ability/operation/agent) are UUID-style:
# either 36-char hyphenated UUID or a slug of [a-zA-Z0-9_-]{1,64}. Either
# way, anchored alphanumeric+hyphen/underscore, bounded length.
ID_RE = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
# Tactic filter (e.g. 'discovery', 'collection') — lowercase alpha only.
TACTIC_RE = re.compile(r'^[a-z][a-z-]{1,30}$')


def _normalize_id(raw):
    if not raw:
        return None
    q = raw.strip()
    return q if ID_RE.match(q) else None


def _normalize_tactic(raw):
    if not raw:
        return None
    q = raw.strip().lower()
    return q if TACTIC_RE.match(q) else None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim(value, n):
    s = str(value or '')
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


# ---- per-subcommand renderers ---------------------------------------------

def _format_list(label, records, columns, max_records):
    """Render a list-style response — table with operator-configurable
    column ordering. `columns` is a list of (field_key, header, width) tuples."""
    if not isinstance(records, list) or not records:
        return f"Caldera: no `{label}` records returned."

    total = len(records)
    truncated = total > max_records
    shown = records[:max_records]

    lines = [f"Caldera {label} — {total} record{'s' if total != 1 else ''}:"]
    lines.append('')
    lines.append('| ' + ' | '.join(h for _, h, _ in columns) + ' |')
    lines.append('| ' + ' | '.join([':-'] * len(columns)) + ' |')
    for r in shown:
        if not isinstance(r, dict):
            continue
        row = []
        for key, _, width in columns:
            v = r.get(key)
            if isinstance(v, list):
                v = ', '.join(str(x) for x in v[:3])
            row.append('`' + _cell(_trim(v if v is not None else '—', width)) + '`')
        lines.append('| ' + ' | '.join(row) + ' |')
    if truncated:
        lines.append(f"_…{total - max_records} more record(s) not shown._")
    return '\n'.join(lines)


def _format_adversary_detail(record):
    if not isinstance(record, dict):
        return None
    rows = [
        ('Adversary', record.get('name') or '?'),
        ('ID', record.get('adversary_id') or record.get('id') or '?'),
    ]
    if record.get('description'):
        rows.append(('Description', _trim(record['description'], 200)))
    if record.get('tags'):
        tags = record['tags']
        if isinstance(tags, list):
            rows.append(('Tags', ', '.join(str(t) for t in tags[:15])))
    atomic = record.get('atomic_ordering') or []
    if isinstance(atomic, list):
        rows.append(('Ability count', len(atomic)))

    lines = [f"Caldera adversary `{record.get('name') or record.get('adversary_id') or '?'}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    # Show first few abilities in the chain.
    if isinstance(atomic, list) and atomic:
        lines.append('')
        lines.append(f"**Atomic ordering (first {min(len(atomic), 10)}):**")
        for i, ab in enumerate(atomic[:10], 1):
            lines.append(f"{i}. `{_cell(ab)}`")
        if len(atomic) > 10:
            lines.append(f"_…{len(atomic) - 10} more ability(ies) not shown._")
    return '\n'.join(lines)


def _format_ability_detail(record):
    if not isinstance(record, dict):
        return None
    rows = [
        ('Ability', record.get('name') or '?'),
        ('ID', record.get('ability_id') or record.get('id') or '?'),
        ('Tactic', record.get('tactic') or '—'),
    ]
    technique = record.get('technique_id') or record.get('technique') or ''
    if technique:
        rows.append(('MITRE technique', technique))
    if record.get('description'):
        rows.append(('Description', _trim(record['description'], 240)))
    platforms = record.get('platforms')
    if isinstance(platforms, list) and platforms:
        rows.append(('Platforms', ', '.join(platforms[:8])))

    lines = [f"Caldera ability `{record.get('name') or record.get('ability_id') or '?'}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")
    return '\n'.join(lines)


def _format_operation_detail(record):
    if not isinstance(record, dict):
        return None
    rows = [
        ('Operation', record.get('name') or '?'),
        ('ID', record.get('id') or '?'),
        ('State', record.get('state') or '—'),
    ]
    if record.get('adversary'):
        adv = record['adversary']
        rows.append(('Adversary', adv.get('name') if isinstance(adv, dict) else adv))
    if record.get('start'):
        rows.append(('Started', record['start']))
    if record.get('group'):
        rows.append(('Agent group', record['group']))
    chain = record.get('chain') or []
    if isinstance(chain, list):
        rows.append(('Chain length', len(chain)))

    lines = [f"Caldera operation `{record.get('name') or record.get('id') or '?'}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")
    return '\n'.join(lines)


# ---- dispatch table -------------------------------------------------------

SUBCOMMANDS = {
    'adversaries': {
        'path':    'adversaries',
        'label':   'adversaries',
        'kind':    'list',
        'columns': [
            ('name',         'Name',          30),
            ('adversary_id', 'ID',            40),
            ('description',  'Description',   60),
        ],
    },
    'adversary': {
        'path':    'adversaries/{id}',
        'label':   'adversary',
        'kind':    'detail',
        'render':  _format_adversary_detail,
    },
    'abilities': {
        'path':    'abilities',
        'label':   'abilities',
        'kind':    'list',
        'columns': [
            ('name',         'Name',          30),
            ('ability_id',   'ID',            40),
            ('tactic',       'Tactic',        15),
            ('technique_id', 'MITRE',         12),
        ],
    },
    'ability': {
        'path':    'abilities/{id}',
        'label':   'ability',
        'kind':    'detail',
        'render':  _format_ability_detail,
    },
    'operations': {
        'path':    'operations',
        'label':   'operations',
        'kind':    'list',
        'columns': [
            ('name',  'Name',  30),
            ('id',    'ID',    36),
            ('state', 'State', 15),
            ('start', 'Started', 24),
        ],
    },
    'operation': {
        'path':    'operations/{id}',
        'label':   'operation',
        'kind':    'detail',
        'render':  _format_operation_detail,
    },
    'agents': {
        'path':    'agents',
        'label':   'agents',
        'kind':    'list',
        'columns': [
            ('paw',      'PAW',        16),
            ('host',     'Host',       30),
            ('platform', 'Platform',   12),
            ('contact',  'Contact',    15),
            ('last_seen', 'Last seen', 24),
        ],
    },
}


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        cmds = ', '.join(f"`{k}`" for k in SUBCOMMANDS)
        return {'messages': [{'text': f"Usage: `@caldera <subcommand> [id]`. Subcommands: {cmds}"}]}

    sub = params[0].lower()
    if sub not in SUBCOMMANDS:
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('caldera', {})
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    verify_tls = bool(getattr(settings, 'VERIFY_TLS', True))
    max_records = int(getattr(settings, 'MAX_RECORDS', 12))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<') or 'caldera.example.com' in base:
        return {'messages': [{'text': 'Caldera is not configured. Set `url` (your Caldera v2 API endpoint) and `key` in `settings.py`.'}]}

    cfg_sub = SUBCOMMANDS[sub]

    # Detail subcommands need an ID; list subcommands accept an optional
    # tactic filter for `abilities`.
    extra_qs = {}
    path = cfg_sub['path']
    if '{id}' in path:
        if len(params) < 2:
            return {'messages': [{'text': f"Usage: `@caldera {sub} <id>` ({cfg_sub['label']})"}]}
        target = _normalize_id(params[1])
        if not target:
            return {'messages': [{'text': f"caldera {sub}: `{_cell(params[1])}` is not a valid ID (alnum + `_-`, 1-64 chars)."}]}
        path = path.replace('{id}', requests.utils.quote(target, safe=''))
    elif sub == 'abilities' and len(params) >= 2:
        # Optional tactic filter on the abilities list.
        tactic = _normalize_tactic(params[1])
        if tactic:
            extra_qs['tactic'] = tactic

    url = base + path
    headers = {
        'KEY': key,                              # Caldera v2 auth header
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot Caldera module',
    }

    try:
        resp = requests.get(
            url,
            params=extra_qs,
            headers=headers,
            allow_redirects=False,
            timeout=(10, 30),
            verify=verify_tls,
        )
    except requests.RequestException as e:
        log.exception("caldera request failed")
        return {'messages': [{'text': f"Caldera request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Caldera: authentication failed — check `key`.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"Caldera: no `{sub}` record found at `{path}`."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Caldera returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("caldera returned non-JSON")
        return {'messages': [{'text': 'Caldera returned a non-JSON response.'}]}

    if cfg_sub['kind'] == 'list':
        # Caldera v2 returns either a top-level list or {data: [...]} —
        # tolerate both.
        records = payload if isinstance(payload, list) else (payload.get('data') if isinstance(payload, dict) else None)
        text = _format_list(cfg_sub['label'], records or [], cfg_sub['columns'], max_records)
    else:
        # Detail returns either the record directly or wrapped under data.
        record = payload.get('data') if isinstance(payload, dict) and isinstance(payload.get('data'), dict) else payload
        text = cfg_sub['render'](record)

    if not text:
        return {'messages': [{'text': f"Caldera: unrecognised response shape for `{sub}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
