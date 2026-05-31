#!/usr/bin/env python3

BINDS = ['@filesec', '@fs']
CHANS = ['debug']
APIURL = {
    'filesec': {
        # FileSec is a curated database of file extensions of interest to
        # attackers (https://filesec.io/). The site serves per-extension
        # JSON; URL_PATTERN below is interpolated with `{ext}` to build
        # the per-lookup URL. No auth required.
        'url_pattern': 'https://filesec.io/api/v1/extensions/{ext}',
        'key': '',
    },
}
CONTENTTYPE = 'application/json'
MAX_REFERENCES = 6
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<file extension>',
        'desc': (
            'Look up a file extension on filesec.io for attack-relevance '
            'metadata: weaponisation status, execution behaviour, common '
            'use cases, and references. No auth required.'
        ),
    },
}
