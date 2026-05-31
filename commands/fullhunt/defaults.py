#!/usr/bin/env python3

BINDS = ['@fullhunt', '@fh']
CHANS = ['debug']
APIURL = {
    'fullhunt': {
        # Free-tier registration at https://fullhunt.io/. Key sent via
        # X-API-KEY header. `auth/status` returns remaining quota.
        'url': 'https://fullhunt.io/api/v1/',
        'key': '<your-fullhunt-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_SUBDOMAINS = 60
MAX_TAGS = 20
MAX_TECH = 20
MAX_COUNTRIES = 10
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '[details|subdomains] <domain>',
        'desc': (
            'FullHunt attack-surface lookup: bare `@fullhunt <domain>` → '
            'asset details (host count, tech fingerprints, countries, tags); '
            '`subdomains <domain>` → subdomain enumeration. Requires a free '
            'FullHunt account (https://fullhunt.io/).'
        ),
    },
}
