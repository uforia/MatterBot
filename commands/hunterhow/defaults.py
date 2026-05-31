#!/usr/bin/env python3

BINDS = ['@hunterhow', '@hh']
CHANS = ['debug']
APIURL = {
    'hunterhow': {
        # Free-tier registration at https://hunter.how/. API key sent as
        # `api-key` query parameter; search query is base64-encoded.
        'url': 'https://api.hunter.how/search',
        'key': '<your-hunterhow-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_RECORDS = 8
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<query|IP|domain>',
        'desc': (
            'Surface search via Hunter.how. Plain IP / domain input is '
            'auto-wrapped (`ip="…"` / `domain="…"`); anything else is '
            'passed verbatim as a Hunter.how query (e.g. '
            '`port=22 country=NL`). Requires a free Hunter.how account '
            '(https://hunter.how/).'
        ),
    },
}
