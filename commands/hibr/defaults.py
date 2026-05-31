#!/usr/bin/env python3

BINDS = ['@hibr', '@hir']
CHANS = ['debug']
APIURL = {
    'hibr': {
        # HaveIBeenRansomed (https://haveibeenransom.com/) tracks
        # organisations listed by ransomware operators. URL_PATTERN is
        # interpolated with `{q}` (urlencoded organisation name) so the
        # operator can retarget if the endpoint changes. Optional `key`
        # is sent via X-API-KEY header when set.
        'url_pattern': 'https://api.haveibeenransom.com/v1/search?q={q}',
        'key': '',
    },
}
CONTENTTYPE = 'application/json'
MAX_HITS = 10
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<organisation name>',
        'desc': (
            'Search HaveIBeenRansomed for a victim organisation. Returns '
            'ransomware operator, date listed, and leak-page URL (defanged) '
            'per hit. Complements `ransomlook` which monitors the leak-site '
            'side. See https://haveibeenransom.com/howapi for setup.'
        ),
    },
}
