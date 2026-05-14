#!/usr/bin/env python3

BINDS = ['@validin', '@vd']
CHANS = ['debug']
APIURL = {
    'validin': {
        # Free-tier registration at https://app.validin.com/. Bearer token via
        # Authorization header.
        'url': 'https://app.validin.com/api/axon/',
        'key': '<your-validin-api-token-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_RECORDS_PER_TYPE = 8
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<domain|IP>',
        'desc': (
            'Validin DNS history lookup for a domain or IP. Auto-routes to '
            '/domains/dns/history or /ips/dns/history. Returns historical '
            'A/AAAA/NS/MX/CNAME/etc. records with first/last-seen timestamps. '
            'Requires a Validin account (https://app.validin.com/).'
        ),
    },
}
