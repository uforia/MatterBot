#!/usr/bin/env python3

BINDS = ['@onyphe', '@op']
CHANS = ['debug']
APIURL = {
    'onyphe': {
        # Free-tier registration at https://www.onyphe.io/. Bearer token via
        # Authorization header; query the free /summary and /simple paths.
        'url': 'https://www.onyphe.io/api/v2/',
        'key': '<your-onyphe-api-token-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_RECORDS = 10
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '[summary|resolver|threatlist|ctl] <target>',
        'desc': (
            'Onyphe lookups: bare `@onyphe <ip>` returns the summary view; '
            '`resolver <ip|host>` for DNS, `threatlist <ip>` for threat-feed '
            'membership, `ctl <domain>` for Certificate Transparency entries. '
            'Requires a free Onyphe account (https://www.onyphe.io/).'
        ),
    },
}
