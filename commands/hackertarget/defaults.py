#!/usr/bin/env python3

BINDS = ['@hackertarget', '@ht']
CHANS = ['debug']
APIURL = {
    'hackertarget': {
        # Free tier: ~50 queries/day per source IP, no auth required.
        # Optional `key` triggers Authorization: Bearer for paid members.
        'url': 'https://api.hackertarget.com/',
        'key': '',
    },
}
CONTENTTYPE = 'text/plain'
MAX_LINES = 60
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<subcommand> <target>',
        'desc': (
            'OSINT toolbox wrapping api.hackertarget.com. Subcommands: '
            '`dns <domain>`, `rdns <ip>`, `subdomains <domain>`, '
            '`whois <domain>`, `geoip <ip>`, `asn <ip>`, `mtr <host>`, '
            '`shareddns <ns>`. No auth required for the free tier '
            '(~50 queries/day per source IP).'
        ),
    },
}
