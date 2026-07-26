#!/usr/bin/env python3

BINDS = ['@wayback', '@waybackmachine', '@wb', '@wm', '@ioc']
CHANS = ['debug']
APIURL = {
    'wayback':
        {
            'url': 'https://archive.org/wayback/available?url=',
            'cdx': 'https://web.archive.org/cdx/search/cdx?url='
        },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<URL>',
        'desc': 'Query the Wayback Machine API for the existence of a URL. Response will '
                'include whether or not the URL is known, the number of snapshots archived '
                'and the oldest and newest snapshots.',
    },
}

# Note: if you use the Wayback Machine API, you may end up being blocked if you overuse
# the API or otherwise hit the rate limits.
