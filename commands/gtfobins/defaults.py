#!/usr/bin/env python3

BINDS = ['@gtfobins', '@gb', '@ioc']
CHANS = ['debug']
APIURL = {
    'gtfobins':   {'url': 'https://gtfobins.github.io/gtfobins.json'},
}
CONTENTTYPE = 'application/json'
CACHE = 'commands/gtfobins/gtfobins.json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Search GTFOBins for information and return any matching entries, such as usage, filenames, etc. '
                'On its first run, the module will build a cache of the GTFOBins website, so the very first query will be '
                'slow.',
    },
    'rebuildcache': {
        'args': None,
        'desc': 'Force a rebuild of the cache. Please use this sparingly and do not overload the GTFOBins website.',
    },
}
