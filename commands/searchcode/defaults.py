#!/usr/bin/env python3

BINDS = ['@searchcode', '@sc']
CHANS = ['debug']
APIURL = {
    'searchcode': {
        # Public code-search API — no auth required.
        # https://searchcode.com/api/
        'url': 'https://searchcode.com/api/',
    },
}
CONTENTTYPE = 'application/json'
MAX_RESULTS = 8
MAX_SNIPPET_CHARS = 240
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<query>',
        'desc': (
            'Search public source code via Searchcode for credential / '
            'keyword leak hunting. Returns filename, repo, language, line '
            'number, and a code snippet. No auth required '
            '(https://searchcode.com/api/).'
        ),
    },
}
