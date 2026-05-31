#!/usr/bin/env python3

BINDS = ['@openmeasures', '@om']
CHANS = ['debug']
APIURL = {
    'openmeasures': {
        # Open Measures public API — https://api.smat-app.com/docs
        # Free tier is ~39 requests/day per source IP, no auth required.
        # A paid key (X-API-KEY header) raises the limit.
        'url': 'https://api.smat-app.com/',
        'key': '',
    },
}
CONTENTTYPE = 'application/json'
# Default platforms searched when the operator doesn't specify --site.
DEFAULT_SITES = 'telegram,bitchute,gab,gettr'
MAX_RESULTS = 8
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<search term>',
        'desc': (
            'Search across alt-tech / fringe social platforms via Open '
            'Measures (Telegram, BitChute, Gab, Gettr, etc.). Free tier '
            '(~39 req/day, no auth) — set `key` in `settings.py` for paid '
            'tier. See https://api.smat-app.com/docs.'
        ),
    },
}
