#!/usr/bin/env python3

import ipaddress
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

HOSTNAME_RE = re.compile(
    r'^(?=.{1,253}$)'
    r'(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)\.)+'
    r'[a-zA-Z]{2,63}$'
)
SHA256_RE = re.compile(r'^[A-Fa-f0-9]{64}$')


def _is_ip(value):
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _classify(raw):
    """Return (normalized, endpoint, label) or (None, None, None).

    Maltiverse exposes resources at /ip, /hostname, /url, /sample. Other hash
    families aren't supported by name — only SHA256 — so MD5/SHA1 are rejected.
    """
    if not raw:
        return None, None, None
    q = raw.strip()
    if SHA256_RE.match(q):
        return q.lower(), 'sample', 'SHA256 sample'

    norm = q.lower().replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    if re.match(r'^hxxps?://', norm):
        norm = norm.replace('hxxps://', 'https://', 1).replace('hxxp://', 'http://', 1)
    if norm.startswith(('http://', 'https://')):
        return norm, 'url', 'URL'

    if _is_ip(norm):
        return norm, 'ip', 'IP'

    # Strip URL path if any before hostname check (CIDR not relevant here).
    norm = norm.split('/', 1)[0]
    if HOSTNAME_RE.match(norm):
        return norm, 'hostname', 'hostname'
    return None, None, None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _maltiverse_id_for_url(url):
    """Maltiverse /url/<id> takes a SHA256 of the URL string as the id.

    Implemented in-process so the operator just passes a URL and the module
    figures out the lookup id.
    """
    import hashlib
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


def _format(query, label, endpoint, payload, max_tags, max_blacklist):
    if not isinstance(payload, dict):
        return None

    rows = []
    rows.append(('Query', f"{query} ({label})"))

    classification = payload.get('classification')
    if classification:
        rows.append(('Classification', classification))

    score = payload.get('score')
    if score is not None:
        rows.append(('Risk score', score))

    first = payload.get('creation_time') or payload.get('first_seen')
    if first:
        rows.append(('First seen', first))
    last = payload.get('modification_time') or payload.get('last_seen')
    if last:
        rows.append(('Last updated', last))

    # IP / hostname-only fields
    if endpoint == 'ip':
        country = payload.get('country_code')
        as_name = payload.get('as_name')
        asn = payload.get('asn_cidr') or payload.get('asn')
        if country:
            rows.append(('Country', country))
        if as_name:
            rows.append(('AS', as_name))
        if asn:
            rows.append(('ASN/CIDR', asn))
    elif endpoint == 'hostname':
        registrar = payload.get('registrar')
        a_records = payload.get('resolved_ip')
        if registrar:
            rows.append(('Registrar', registrar))
        if isinstance(a_records, list) and a_records:
            ips = ', '.join(str((r.get('ip_addr') if isinstance(r, dict) else r) or '?') for r in a_records[:5])
            extra = '' if len(a_records) <= 5 else f", …(+{len(a_records) - 5})"
            rows.append(('Resolved IPs', ips + extra))
    elif endpoint == 'sample':
        file_type = payload.get('file_type') or payload.get('type')
        md5 = payload.get('md5')
        sha1 = payload.get('sha1')
        if file_type:
            rows.append(('File type', file_type))
        if md5:
            rows.append(('MD5', md5))
        if sha1:
            rows.append(('SHA1', sha1))

    tags = payload.get('tag') or payload.get('tags') or []
    if isinstance(tags, list) and tags:
        capped = tags[:max_tags]
        tag_str = ', '.join(_cell(t) for t in capped)
        if len(tags) > max_tags:
            tag_str += f", …(+{len(tags) - max_tags})"
        rows.append(('Tags', tag_str))

    lines = [f"Maltiverse record for `{query}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    ref_id = payload.get('_id') or payload.get('id')
    if ref_id:
        # /sample/<sha256>, /ip/<ip>, /hostname/<host>, /url/<sha256-of-url>
        lines.append(f"| Reference | [Maltiverse {endpoint} page](https://maltiverse.com/{endpoint}/{ref_id}) |")

    blacklist = payload.get('blacklist') or []
    if isinstance(blacklist, list) and blacklist:
        total = len(blacklist)
        truncated = total > max_blacklist
        shown = blacklist[:max_blacklist]
        lines.append('')
        lines.append(f"**Blacklist entries ({len(shown)} of {total}):**")
        for entry in shown:
            if not isinstance(entry, dict):
                continue
            src = entry.get('source') or entry.get('name') or '?'
            desc = entry.get('description') or ''
            first_seen = entry.get('first_seen') or ''
            line = f"- `{_cell(src)}`"
            if first_seen:
                line += f" · `{_cell(first_seen)}`"
            if desc:
                line += f" — {_cell(desc)[:120]}"
            lines.append(line)
        if truncated:
            lines.append(f"_…{total - max_blacklist} more not shown._")

    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    raw = params[0]
    query, endpoint, label = _classify(raw)
    if not query:
        # Silent no-op on shape mismatch (matches @ioc convention).
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('maltiverse', {})
    token = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_tags = int(getattr(settings, 'MAX_TAGS', 15))
    max_blacklist = int(getattr(settings, 'MAX_BLACKLIST', 8))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not token or token.startswith('<'):
        return {'messages': [{'text': 'Maltiverse is not configured. Set `key` in `settings.py` (free token at https://maltiverse.com/).'}]}

    # For /url, the lookup id is sha256(url). For everything else, the
    # resource value goes in the path verbatim (urlencoded so : and / can't
    # reshape the request URL).
    path_id = _maltiverse_id_for_url(query) if endpoint == 'url' else query
    url = base + endpoint + '/' + requests.utils.quote(path_id, safe='')

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot Maltiverse module',
    }

    try:
        resp = requests.get(
            url,
            headers=headers,
            allow_redirects=False,
            timeout=(10, 30),
        )
    except requests.RequestException as e:
        log.exception("maltiverse request failed")
        return {'messages': [{'text': f"Maltiverse request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'Maltiverse: authentication failed — check the bearer token.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'Maltiverse: rate-limited (HTTP 429). Free tier quota may be exhausted.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"Maltiverse: no record for `{query}`."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"Maltiverse returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("maltiverse returned non-JSON")
        return {'messages': [{'text': 'Maltiverse returned a non-JSON response.'}]}

    text = _format(query, label, endpoint, payload, max_tags, max_blacklist)
    if not text:
        return {'messages': [{'text': f"Maltiverse: unrecognised response shape for `{query}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
