#!/usr/bin/env python3

BINDS = ['@chainabuse', '@ca', '@ioc']
CHANS = ['debug']
APIURL = {
    'chainabuse': {
        # Free registration at https://www.chainabuse.com/. The API key is
        # sent as the username component of HTTP Basic auth (empty password).
        'url': 'https://api.chainabuse.com/v0/',
        'key': '<your-chainabuse-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_REPORTS = 5
MAX_DESC_CHARS = 300
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<crypto address>',
        'desc': 'Query ChainAbuse for abuse reports tied to a cryptocurrency address (BTC, ETH, SOL, …). Returns total report count, scam categories, and recent report descriptions. Requires a free ChainAbuse account (https://www.chainabuse.com/).',
    },
}
