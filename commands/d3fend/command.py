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

# ATT&CK technique IDs: T<4 digits>, optionally with .<3 digits> sub-technique
# suffix. Case-insensitive accept, uppercase-normalised output.
ATTACK_RE = re.compile(r'^T(\d{4})(?:\.(\d{3}))?$', re.IGNORECASE)


def _normalize_attack_id(raw):
    if not raw:
        return None
    m = ATTACK_RE.match(raw.strip())
    if not m:
        return None
    if m.group(2):
        return f"T{m.group(1)}.{m.group(2)}"
    return f"T{m.group(1)}"


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _trim(value, n):
    s = str(value or '')
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _walk_counters(payload):
    """Walk the JSON-LD response from /offensive-technique/attack/<T-id> and
    yield (d3fend_id, label, definition) per counter-technique.

    D3FEND's payload is JSON-LD with nested @graph nodes; the response shape
    has drifted between API versions. We try the two documented surfaces in
    order, falling through to a recursive walk if neither matches.
    """
    if not isinstance(payload, dict):
        return

    def _emit(node):
        if not isinstance(node, dict):
            return
        nid = node.get('@id') or node.get('id') or ''
        label = node.get('d3f:display-name') or node.get('rdfs:label') or node.get('label') or ''
        defn = node.get('d3f:definition') or node.get('rdfs:comment') or node.get('definition') or ''
        if not isinstance(nid, str) or ('d3f:' not in nid and not nid.startswith('D3-')):
            return
        short = nid.split(':', 1)[-1] if ':' in nid else nid
        # Filter out ATT&CK technique nodes (d3f:T1055 etc.) — they share the
        # d3f: namespace with D3FEND counters in the response, but they are
        # the OFFENSIVE technique being queried, not a defensive counter.
        if ATTACK_RE.match(short):
            return
        yield (short, label, defn)

    # Documented v0 surface: payload['off_to_def']['@graph'][*]
    off_to_def = payload.get('off_to_def') or payload.get('offToDef') or payload.get('result')
    if isinstance(off_to_def, dict):
        graph = off_to_def.get('@graph') or off_to_def.get('graph')
        if isinstance(graph, list):
            for node in graph:
                if not isinstance(node, dict):
                    continue
                # Each top-level @graph node may carry `d3f:countered-by` →
                # nested @graph with the actual D3FEND techniques.
                cb = node.get('d3f:countered-by') or node.get('countered-by') or {}
                if isinstance(cb, dict):
                    inner = cb.get('@graph') or cb.get('graph') or []
                    if isinstance(inner, list):
                        for inode in inner:
                            yield from _emit(inode)
                # Some flat responses put the techniques directly at the
                # top-level @graph.
                yield from _emit(node)

    # Fallback: recursive search for nodes that look like D3FEND techniques.
    seen = set()
    stack = [payload]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            nid = cur.get('@id') or ''
            if isinstance(nid, str) and ('d3f:' in nid) and nid not in seen:
                seen.add(nid)
                short = nid.split(':', 1)[-1] if ':' in nid else nid
                if not ATTACK_RE.match(short):
                    label = cur.get('d3f:display-name') or cur.get('rdfs:label') or cur.get('label') or ''
                    defn = cur.get('d3f:definition') or cur.get('rdfs:comment') or cur.get('definition') or ''
                    yield (short, label, defn)
            for v in cur.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            for v in cur:
                if isinstance(v, (dict, list)):
                    stack.append(v)


def _format(attack_id, payload, max_counters):
    counters = []
    seen = set()
    for short, label, defn in _walk_counters(payload):
        if short in seen:
            continue
        seen.add(short)
        counters.append((short, label, defn))

    lines = [f"D3FEND counters for `{attack_id}` — [ATT&CK detail](https://attack.mitre.org/techniques/{attack_id.replace('.', '/')}):"]

    if not counters:
        lines.append('_No D3FEND counter-techniques found in the response._')
        return '\n'.join(lines)

    total = len(counters)
    truncated = total > max_counters
    shown = counters[:max_counters]

    lines.append('')
    lines.append('| D3FEND technique | Label | Definition |')
    lines.append('| :- | :- | :- |')
    for short, label, defn in shown:
        lines.append(f"| `{_cell(short)}` | `{_cell(_trim(label, 50))}` | `{_cell(_trim(defn, 200))}` |")
    if truncated:
        lines.append(f"_…{total - max_counters} more counter(s) not shown._")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{'text': "Usage: `@d3fend <ATT&CK technique ID>` (e.g. `@d3fend T1055`)."}]}

    attack_id = _normalize_attack_id(params[0])
    if not attack_id:
        return {'messages': [{'text': f"D3FEND: `{_cell(params[0])}` is not a valid ATT&CK technique ID (expected `T<NNNN>` or `T<NNNN>.<NNN>`)."}]}

    cfg = getattr(settings, 'APIURL', {}).get('d3fend', {})
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_counters = int(getattr(settings, 'MAX_COUNTERS', 15))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    url = base + 'offensive-technique/attack/' + requests.utils.quote(attack_id, safe='') + '.json'
    try:
        resp = requests.get(
            url,
            headers={
                'Accept': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot MITRE D3FEND module',
            },
            allow_redirects=True,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("d3fend request failed")
        return {'messages': [{'text': f"D3FEND request failed: `{e}`"}]}

    if resp.status_code == 404:
        return {'messages': [{'text': f"D3FEND: no record for `{attack_id}` — the technique may have no documented counters."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"D3FEND returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("d3fend returned non-JSON")
        return {'messages': [{'text': 'D3FEND returned a non-JSON response.'}]}

    text = _format(attack_id, payload, max_counters)
    if not text:
        return {'messages': [{'text': f"D3FEND: unrecognised response shape for `{attack_id}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
