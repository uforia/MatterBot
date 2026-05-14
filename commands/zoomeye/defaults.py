#!/usr/bin/env python3

# NOTE: Zoomeye is intentionally NOT bound to @ioc by default.
# Surface-search queries are routed through a CN-hosted cloud service;
# data-sovereignty and cross-border ToS considerations are an operator
# call. The module ships ENABLED for direct @zoomeye use; the @ioc
# auto-fanout requires a one-line edit to BINDS in settings.py.
BINDS = ['@zoomeye', '@zm']
CHANS = ['debug']
APIURL = {
    'zoomeye': {
        # Free registration at https://www.zoomeye.ai/. Key sent via
        # API-KEY header.
        'url': 'https://api.zoomeye.ai/v2/',
        'key': '<your-zoomeye-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_RECORDS = 8
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<query|IP|domain>',
        'desc': (
            'Zoomeye surface search. Plain IP / domain input is auto-wrapped '
            '(`ip:"…"` / `hostname:"…"`); anything else is passed verbatim '
            'as a Zoomeye query. Requires a free Zoomeye account '
            '(https://www.zoomeye.ai/).'
        ),
    },
}
