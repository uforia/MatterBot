#!/usr/bin/env python3

BINDS = ['@d3fend', '@d3']
CHANS = ['debug']
APIURL = {
    'd3fend': {
        # MITRE D3FEND knowledge graph — no auth, public API.
        # https://d3fend.mitre.org/api-docs/
        'url': 'https://d3fend.mitre.org/api/',
        'key': '',
    },
}
CONTENTTYPE = 'application/json'
MAX_COUNTERS = 15
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<ATT&CK technique ID>',
        'desc': (
            'Look up defensive D3FEND counter-techniques for a given '
            'ATT&CK technique (e.g. `@d3fend T1055`, `@d3fend T1055.012`). '
            'Companion to the @attackmatrix command. No auth required.'
        ),
    },
}
