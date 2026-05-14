#!/usr/bin/env python3

# Local-tool wrap (no @ioc binding — explicit invocation only, since the
# probe makes outbound HTTP requests).
BINDS = ['@httpx', '@hx']
CHANS = ['debug']
# Optional explicit path to the projectdiscovery httpx binary. Leave empty to
# pick it up from $PATH via shutil.which('httpx'). Useful when httpx is
# installed at ~/go/bin/httpx and not on the bot's PATH.
HTTPX_BIN = ''
# Operator-configurable safety knobs.
TIMEOUT_SECS = 30
MAX_TARGETS = 1
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<URL|host[:port]>',
        'desc': 'Probe a single URL or hostname with the ProjectDiscovery httpx CLI and surface status, title, server, technologies, content length, and TLS. Requires the httpx binary on $PATH (or set HTTPX_BIN in settings.py).',
    },
}
