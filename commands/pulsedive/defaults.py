#!/usr/bin/env python3

BINDS = ['@pulsedive', '@pd', '@ioc']
CHANS = ['debug']
APIURL = {
    'pulsedive': {
        # Free-tier registration at https://pulsedive.com/. The free key
        # works for the /info.php and /indicator.php read endpoints used
        # here; the higher-volume scan/analyze flow requires a paid key.
        'url': 'https://pulsedive.com/api/',
        'key': '<your-pulsedive-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_THREATS = 12
MAX_FEEDS = 12
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<IP|domain|URL|MD5|SHA1|SHA256>',
        'desc': 'Query PulseDive for indicator enrichment: risk level, threats, feeds, first/last seen. Auto-detects type. Requires a free PulseDive account (https://pulsedive.com/).',
    },
}
