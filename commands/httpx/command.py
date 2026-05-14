#!/usr/bin/env python3

import json
import re
import shutil
import subprocess

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

# Strict input: optional scheme, then RFC-1123 hostname OR strict IPv4 dotted
# quad, optional :port, optional /path. Used as the trust boundary — the
# validated string is passed to httpx via list-form subprocess (no shell), so
# nothing inside this pattern needs additional shell escaping, but everything
# outside it (whitespace, `;`, `|`, `$`, `&`, backtick, leading `-`) is rejected.
_IPV4_OCTET = r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
TARGET_RE = re.compile(
    r'^'
    r'(?:(?:https?|hxxps?)://)?'                                          # optional scheme
    r'(?:'
        r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+'           # hostname labels
        r'[a-zA-Z]{2,63}'                                                 # TLD
        r'|'
        rf'{_IPV4_OCTET}(?:\.{_IPV4_OCTET}){{3}}'                          # IPv4 dotted quad (each octet 0-255)
    r')'
    r'(?::[0-9]{1,5})?'                                                   # optional port
    r"(?:/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]*)?"                        # optional path
    r'$'
)


def _normalize(raw):
    if not raw:
        return None
    q = raw.strip()
    # Defang restore — only the host portion typically gets defanged.
    q = q.replace('[.]', '.').replace('(.)', '.').replace('[:]', ':')
    q = re.sub(r'^hxxps?://', lambda m: m.group(0).replace('hxxp', 'http'), q, flags=re.IGNORECASE)
    if not TARGET_RE.match(q):
        return None
    return q


def _cell(value):
    return str(value).replace('`', '').replace('|', '/').replace('\n', ' ').replace('\r', '')


def _format_result(target, rec):
    """Render a single httpx -json record as a markdown table."""
    if not isinstance(rec, dict):
        return None
    rows = []
    url = rec.get('url') or target
    status = rec.get('status_code')
    if status is not None:
        rows.append(('Status', status))
    title = rec.get('title')
    if title:
        rows.append(('Title', title))
    server = rec.get('webserver') or rec.get('server')
    if server:
        rows.append(('Server', server))
    content_type = rec.get('content_type')
    if content_type:
        rows.append(('Content-Type', content_type))
    length = rec.get('content_length')
    if length is not None:
        rows.append(('Content-Length', length))
    tech = rec.get('tech') or rec.get('technologies')
    if tech:
        if isinstance(tech, list):
            tech_str = ', '.join(str(t) for t in tech[:30])
            if len(tech) > 30:
                tech_str += f", …(+{len(tech) - 30})"
        else:
            tech_str = str(tech)
        rows.append(('Tech', tech_str))
    host = rec.get('host')
    if host:
        rows.append(('Resolved IP', host))
    cdn = rec.get('cdn_name') or rec.get('cdn')
    if cdn:
        rows.append(('CDN', cdn))
    tls = rec.get('tls')
    if isinstance(tls, dict):
        cn = tls.get('subject_cn') or tls.get('subject_common_name')
        issuer = tls.get('issuer_cn') or tls.get('issuer_organization')
        if cn:
            rows.append(('TLS CN', cn))
        if issuer:
            rows.append(('TLS Issuer', issuer if isinstance(issuer, str) else ', '.join(map(str, issuer))[:200]))
    time = rec.get('time') or rec.get('response_time')
    if time:
        rows.append(('Response time', time))

    if not rows:
        return None

    lines = [f"httpx probe for `{url}`:"]
    lines.append('| Field | Value |')
    lines.append('| :- | :- |')
    for k, v in rows:
        lines.append(f"| **{_cell(k)}** | `{_cell(v)}` |")
    return '\n'.join(lines)


def _is_projectdiscovery_httpx(path):
    """Probe a candidate `httpx` binary and verify it's ProjectDiscovery's.

    A common collision: `pip install httpx[cli]` (or any transitive dep that
    pulls in the python httpx HTTP-client library with its `[cli]` extra)
    installs a script named `httpx` in the venv's bin/. `shutil.which('httpx')`
    then finds the Python one first. Python httpx CLI expects
    `httpx [OPTIONS] [METHOD] URL`, NOT the `-u <target> -json -tech-detect`
    argv shape we use; the subprocess fails / returns garbage.

    Filter at resolution time so the operator gets a clear "wrong binary"
    message instead of a confusing subprocess error later.
    """
    try:
        proc = subprocess.run(
            [path, '-version'],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    blob = ((proc.stdout or '') + (proc.stderr or '')).lower()
    # ProjectDiscovery httpx -version output contains "projectdiscovery"
    # and/or "current version". Python httpx CLI doesn't recognise the
    # single-dash `-version` flag and emits an argparse error, missing
    # both signatures.
    return 'projectdiscovery' in blob or 'current version' in blob


def _resolve_binary():
    """Return a path to ProjectDiscovery's `httpx` binary, or None.

    Probes each candidate with `_is_projectdiscovery_httpx` so a Python
    httpx[cli] script on PATH doesn't get picked up by accident.
    """
    candidates = []
    explicit = (getattr(settings, 'HTTPX_BIN', '') or '').strip()
    if explicit:
        if Path(explicit).is_file():
            candidates.append(explicit)
        else:
            found = shutil.which(explicit)
            if found:
                candidates.append(found)
    if not candidates:
        # Fall back to PATH lookup for the bare name.
        found = shutil.which('httpx')
        if found:
            candidates.append(found)
    for path in candidates:
        if _is_projectdiscovery_httpx(path):
            return path
    return None


def process(command, channel, username, params, files, conn):
    messages = []
    if not params:
        return {'messages': messages}

    raw = params[0]
    target = _normalize(raw)
    if not target:
        return {'messages': [{'text': f"httpx: `{raw}` doesn't look like a URL or hostname (rejected)."}]}

    binary = _resolve_binary()
    if not binary:
        # Distinguish "nothing on PATH" from "wrong tool on PATH" so the
        # operator gets actionable guidance.
        on_path = shutil.which('httpx')
        if on_path:
            return {'messages': [{
                'text': (
                    f"httpx binary at `{on_path}` does NOT look like "
                    "ProjectDiscovery httpx (`-version` probe failed). "
                    "It's almost certainly the **Python httpx HTTP-client CLI** "
                    "(installed by `pip install httpx[cli]` or pulled in as a "
                    "transitive dep). Install ProjectDiscovery's separately — "
                    "`go install github.com/projectdiscovery/httpx/cmd/httpx@latest` — "
                    "and either put it earlier in `$PATH` or set `HTTPX_BIN` in "
                    "`settings.py` to an absolute path."
                )
            }]}
        return {'messages': [{
            'text': (
                "httpx binary not found. Install ProjectDiscovery httpx "
                "(`go install github.com/projectdiscovery/httpx/cmd/httpx@latest`) "
                "and ensure it's on $PATH, or set `HTTPX_BIN` in `settings.py`. "
                "Note: this is NOT the python `httpx` HTTP-client library."
            )
        }]}

    timeout_secs = int(getattr(settings, 'TIMEOUT_SECS', 30))
    max_chars = int(getattr(settings, 'MAX_OUTPUT_CHARS', 8000))

    # List-form subprocess: each arg is a separate list entry so the target
    # value cannot be re-interpreted by a shell. No shell=True, no string
    # concatenation.
    argv = [
        binary,
        '-u', target,
        '-json',
        '-no-color',
        '-silent',
        '-tech-detect',
        '-title',
        '-status-code',
        '-content-length',
        '-content-type',
        '-server',
        '-tls-probe',
        '-timeout', '15',
        '-follow-redirects',
        '-max-redirects', '5',
    ]

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_secs,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {'messages': [{'text': f"httpx timed out after {timeout_secs}s on `{target}`."}]}
    except (OSError, ValueError) as e:
        log.exception("httpx subprocess failed")
        return {'messages': [{'text': f"httpx failed to launch: `{e}`"}]}

    if proc.returncode != 0 and not proc.stdout.strip():
        stderr_tail = (proc.stderr or '').strip().splitlines()[-1:] or ['(no stderr)']
        return {'messages': [{'text': f"httpx exited with code {proc.returncode}: {_cell(stderr_tail[0])}"}]}

    # httpx -json emits one JSON object per line. With -u <single>, expect 1.
    rec = None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        # First valid record wins.
        break

    if rec is None:
        return {'messages': [{'text': f"httpx returned no probe result for `{target}` — host may be unreachable or filtered."}]}

    text = _format_result(target, rec)
    if not text:
        return {'messages': [{'text': f"httpx returned an unparseable record for `{target}`."}]}

    if len(text) > max_chars:
        text = text[:max_chars - 32].rsplit('\n', 1)[0] + '\n_…output truncated._'

    messages.append({'text': text})
    return {'messages': messages}
