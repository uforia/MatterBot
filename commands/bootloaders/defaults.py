#!/usr/bin/env python3

BINDS = ['@bootloaders', '@bl', '@ioc']
CHANS = ['debug']
APIURL = {
    'bootloaders':   {'url': 'https://www.bootloaders.io/api/bootloaders.json'},
}
CONTENTTYPE = 'application/json'
CACHE = 'commands/bootloaders/bootloaders.json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Search Bootloaders for information and return any matching entries, such as hashes, filenames, etc. '
                'On its first run, the module will build a cache of the Bootloaders website, so the very first query will be '
                'slow.',
    },
    'rebuildcache': {
        'args': None,
        'desc': 'Force a rebuild of the cache. Please use this sparingly and do not overload the Bootloaders website.',
    },
}
