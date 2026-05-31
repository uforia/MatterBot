#!/usr/bin/env python3

BINDS = ['@apivoid', '@av']
CHANS = ['debug']
APIURL = {
    'apivoid': {
        # Free credits at signup; pay-as-you-go endpoints used here.
        # Key sent as `key` query parameter (APIVoid's documented shape).
        # https://docs.apivoid.com/
        'url': 'https://endpoint.apivoid.com/',
        'key': '<your-apivoid-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_DETECTIONS = 10
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<iprep|domainrep|urlrep|dnslookup> <target>',
        'desc': (
            'APIVoid lookups. Subcommands: `iprep <ip>`, '
            '`domainrep <domain>`, `urlrep <url>`, `dnslookup <domain>`. '
            'Each consumes pay-as-you-go credits. Requires an APIVoid '
            'account (https://www.apivoid.com/).'
        ),
    },
}
