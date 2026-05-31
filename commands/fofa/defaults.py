#!/usr/bin/env python3

# NOTE: Fofa is intentionally NOT bound to @ioc by default.
# Surface-search queries are routed through a CN-hosted cloud service.
# Same opt-in pattern as the Kaspersky / Zoomeye modules: ships
# enabled for direct @fofa use; the @ioc auto-fanout requires
# operator-side BINDS edit in settings.py.
BINDS = ['@fofa', '@ff']
CHANS = ['debug']
APIURL = {
    'fofa': {
        # Free-tier registration at https://en.fofa.info/. Auth is the
        # account email plus an API key — both passed as query
        # parameters per Fofa's documented API shape.
        'url':   'https://fofa.info/api/v1/search/all',
        'email': '<your-fofa-account-email-here>',
        'key':   '<your-fofa-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_RECORDS = 8
# Fields requested per record. Order matters — Fofa returns parallel
# lists per row in the same order as the `fields` query param.
FOFA_FIELDS = 'host,ip,port,protocol,country_name,as_organization,server,title'
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<query|IP|domain>',
        'desc': (
            'Fofa surface search. Plain IP / domain input is auto-wrapped '
            '(`ip="…"` / `domain="…"`); anything else is passed verbatim as '
            'a Fofa query (e.g. `port="22" && country="CN"`). Requires a '
            'free Fofa account (https://en.fofa.info/).'
        ),
    },
}
