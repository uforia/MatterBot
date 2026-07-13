#!/usr/bin/env python3

BINDS = ['@threatrip', '@tr', '@ioc']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
ACCEPTS = ['ip', 'ipv6', 'domain', 'url', 'md5', 'sha1', 'sha256']
CHANS = ['debug']
APIURL = {
    'threatrip': {
        # ThreatRip threat-intel platform (https://www.threat.rip/).
        # URL_PATTERN is interpolated with `{type}` and `{value}` so the
        # operator can retarget if the API path changes. Bearer-token
        # auth via Authorization header.
        # Docs: https://neikidev.github.io/tip-v2/api-docs-v1.html
        'url_pattern': 'https://api.threat.rip/v1/{type}/{value}',
        'key': '<your-threatrip-api-token-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_TAGS = 15
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<IP|domain|URL|MD5|SHA1|SHA256>',
        'desc': (
            'ThreatRip threat-intelligence lookup. Auto-detects indicator '
            'type and returns severity / score, tags, threat-actor / '
            'campaign attribution, and first/last seen. Requires a '
            'ThreatRip account (https://www.threat.rip/).'
        ),
    },
}
