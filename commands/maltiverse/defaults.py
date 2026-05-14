#!/usr/bin/env python3

BINDS = ['@maltiverse', '@mv', '@ioc']
CHANS = ['debug']
APIURL = {
    'maltiverse': {
        # Free registration at https://maltiverse.com/. Bearer token required.
        'url': 'https://api.maltiverse.com/',
        'key': '<your-maltiverse-bearer-token-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_TAGS = 15
MAX_BLACKLIST = 8
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<IP|hostname|URL|SHA256>',
        'desc': 'Query Maltiverse for classification (malicious/suspicious/neutral/whitelist), tags, blacklist entries, and first/last seen. Auto-detects the resource type. Requires a free Maltiverse account (https://maltiverse.com/).',
    },
}
