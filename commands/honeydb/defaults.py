#!/usr/bin/env python3

BINDS = ['@honeydb', '@hdb', '@ioc']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
ACCEPTS = ['ip', 'ipv6']
CHANS = ['debug']
APIURL = {
    'honeydb': {
        # API root — endpoints used: /threat-info/<ip> and /ip-history/<ip>.
        'url': 'https://honeydb.io/api/',
        # Free registration required (https://honeydb.io/) — both fields needed.
        'id':  '<your-honeydb-api-id-here>',
        'key': '<your-honeydb-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_HISTORY_ROWS = 30
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<IPv4|IPv6> [history]',
        'desc': 'Query HoneyDB for honeypot activity on an IP address. Default returns aggregated threat info (last seen, hit count, ports, services). Add `history` for the per-day history endpoint. Requires a free HoneyDB account (https://honeydb.io/).',
    },
}
