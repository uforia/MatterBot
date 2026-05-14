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

HOSTNAME_RE = re.compile(
    r'^(?=.{1,253}$)'
    r'(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)\.)+'
    r'[a-zA-Z]{2,63}$'
)


def _normalize_domain(raw):
    if not raw:
        return None
    q = raw.strip().lower()
    q = q.replace('[.]', '.').replace('(.)', '.')
    q = re.sub(r'^(?:https?|hxxps?)://', '', q)
    q = q.split('/', 1)[0]
    return q if HOSTNAME_RE.match(q) else None


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _capped_list(values, cap, label):
    if not values:
        return None
    capped = values[:cap]
    s = ', '.join(_cell(v) for v in capped)
    if len(values) > cap:
        s += f", …(+{len(values) - cap} more)"
    return s


def _format_details(domain, payload, max_tags, max_tech, max_countries):
    if not isinstance(payload, dict):
        return None

    meta = payload.get('metadata') or {}
    # FullHunt sometimes returns the metadata fields at the payload root too;
    # try both layers.
    def _g(k):
        return meta.get(k) if isinstance(meta, dict) and k in meta else payload.get(k)

    rows = [('Domain', domain)]

    exists = _g('exists')
    if exists is not None:
        rows.append(('Exists', 'yes' if exists else 'no'))

    host_count = _g('host_count') or _g('hosts_count')
    if host_count is not None:
        rows.append(('Host count', host_count))

    first = _g('first_seen') or _g('first_observed')
    last = _g('last_seen') or _g('last_observed')
    if first:
        rows.append(('First seen', first))
    if last:
        rows.append(('Last seen', last))

    tags = _g('tags') or []
    tags_str = _capped_list(tags if isinstance(tags, list) else [tags], max_tags, 'tags')
    if tags_str:
        rows.append(('Tags', tags_str))

    tech = _g('tech') or _g('technologies') or []
    tech_str = _capped_list(tech if isinstance(tech, list) else [tech], max_tech, 'tech')
    if tech_str:
        rows.append(('Tech', tech_str))

    countries = _g('country') or _g('countries') or []
    if isinstance(countries, str):
        countries = [countries]
    country_str = _capped_list(countries, max_countries, 'countries')
    if country_str:
        rows.append(('Countries', country_str))

    lines = [f"FullHunt details for `{domain}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")

    lines.append(f"| Reference | [FullHunt domain page](https://fullhunt.io/domain/{domain}) |")
    return '\n'.join(lines)


def _format_subdomains(domain, payload, max_subdomains):
    if not isinstance(payload, dict):
        return None
    hosts = payload.get('hosts') or payload.get('subdomains') or []
    if not isinstance(hosts, list):
        return None

    total = len(hosts)
    if total == 0:
        return f"FullHunt: no subdomains found for `{domain}`."

    truncated = total > max_subdomains
    shown = hosts[:max_subdomains]

    lines = [f"FullHunt subdomains for `{domain}` — {len(shown)} of {total}:"]
    lines.append('```')
    for h in shown:
        if isinstance(h, str):
            lines.append(h)
        elif isinstance(h, dict):
            # Some FullHunt response variants nest each host as
            # {host: "...", ip: "...", ports: [...]}.
            host = h.get('host') or h.get('hostname') or '?'
            ip = h.get('ip')
            extras = []
            if ip:
                extras.append(str(ip))
            ports = h.get('ports')
            if isinstance(ports, list) and ports:
                extras.append('ports=' + ','.join(str(p) for p in ports[:8]))
            lines.append(host + (f" [{' | '.join(extras)}]" if extras else ''))
    lines.append('```')
    if truncated:
        lines.append(f"_…{total - max_subdomains} more subdomain(s) not shown._")
    return '\n'.join(lines)


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': [{
            'text': "Usage: `@fullhunt [details|subdomains] <domain>` — bare `@fullhunt <domain>` defaults to `details`."
        }]}

    sub = 'details'
    target = params[0]
    if params[0].lower() in ('details', 'subdomains') and len(params) >= 2:
        sub = params[0].lower()
        target = params[1]

    domain = _normalize_domain(target)
    if not domain:
        if params[0].lower() in ('details', 'subdomains'):
            return {'messages': [{'text': f"fullhunt {sub}: `{_cell(target)}` is not a valid domain."}]}
        return {'messages': messages}

    cfg = getattr(settings, 'APIURL', {}).get('fullhunt', {})
    key = cfg.get('key') or ''
    base = (cfg.get('url') or '').rstrip('/') + '/'
    max_subdomains = int(getattr(settings, 'MAX_SUBDOMAINS', 60))
    max_tags = int(getattr(settings, 'MAX_TAGS', 20))
    max_tech = int(getattr(settings, 'MAX_TECH', 20))
    max_countries = int(getattr(settings, 'MAX_COUNTRIES', 10))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    if not key or key.startswith('<'):
        return {'messages': [{'text': 'FullHunt is not configured. Set `key` in `settings.py` (free registration at https://fullhunt.io/).'}]}

    endpoint = f"domain/{requests.utils.quote(domain, safe='')}/{'subdomains' if sub == 'subdomains' else 'details'}"
    url = base + endpoint
    headers = {
        'X-API-KEY': key,
        'Accept': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot FullHunt module',
    }

    try:
        resp = requests.get(url, headers=headers, allow_redirects=False, timeout=(10, 30))
    except requests.RequestException as e:
        log.exception("fullhunt request failed")
        return {'messages': [{'text': f"FullHunt request failed: `{e}`"}]}

    if resp.status_code == 401 or resp.status_code == 403:
        return {'messages': [{'text': 'FullHunt: authentication failed — check `key`.'}]}
    if resp.status_code == 429:
        return {'messages': [{'text': 'FullHunt: rate-limited (HTTP 429). Free-tier quota may be exhausted.'}]}
    if resp.status_code == 404:
        return {'messages': [{'text': f"FullHunt: no record for `{domain}` ({sub})."}]}
    if resp.status_code != 200:
        return {'messages': [{'text': f"FullHunt returned HTTP {resp.status_code}."}]}

    try:
        payload = resp.json()
    except ValueError:
        log.exception("fullhunt returned non-JSON")
        return {'messages': [{'text': 'FullHunt returned a non-JSON response.'}]}

    if sub == 'subdomains':
        text = _format_subdomains(domain, payload, max_subdomains)
    else:
        text = _format_details(domain, payload, max_tags, max_tech, max_countries)

    if not text:
        return {'messages': [{'text': f"FullHunt: unrecognised response shape for `{domain}` ({sub})."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
