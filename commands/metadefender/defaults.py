#!/usr/bin/env python3

BINDS = ['@metadefender', '@md', '@ioc']
CHANS = ['debug']
APIURL = {
    'metadefender': {
        # Free-tier registration at https://metadefender.opswat.com/.
        # API key sent via `apikey` header.
        'url': 'https://api.metadefender.com/v4/',
        'key': '<your-metadefender-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_ENGINES = 8
MAX_SOURCES = 8
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<IP|domain|MD5|SHA1|SHA256>',
        'desc': (
            'OPSWAT MetaDefender Cloud reputation lookup — multi-engine scan '
            'results for hashes, plus IP/domain reputation across threat '
            'feeds. Auto-detects input type. Requires a free MetaDefender '
            'account (https://metadefender.opswat.com/).'
        ),
    },
}
