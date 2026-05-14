#!/usr/bin/env python3

BINDS = ['@netlas', '@nl']
CHANS = ['debug']
APIURL = {
    'netlas': {
        # Free-tier registration at https://netlas.io/. Key sent as
        # X-API-Key header.
        'url': 'https://app.netlas.io/api/',
        'key': '<your-netlas-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_PORTS = 20
MAX_DOMAINS = 15
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '[host|whois] <IP|domain>',
        'desc': (
            'Netlas lookups: bare `@netlas <ip|host>` returns the host record '
            '(ports, services, geolocation). `whois <ip|domain>` for the '
            'whois record. Requires a free Netlas account '
            '(https://netlas.io/).'
        ),
    },
}
