#!/usr/bin/env python3

BINDS = ['@loldrivers', '@ld', '@ioc']
CHANS = ['debug']
APIURL = {
    'loldrivers':   {'url': 'https://www.loldrivers.io/api/drivers.json'},
}
CONTENTTYPE = 'application/json'
CACHE = 'commands/loldrivers/loldrivers.json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Search loldrivers for information and return any matching entries, such as hashes, filenames, etc. '
                'On its first run, the module will build a cache of the unprotect.it website, so the very first query will be '
                'slow.',
    },
    'rebuildcache': {
        'args': None,
        'desc': 'Force a rebuild of the cache. Please use this sparingly and do not overload the LOLDrivers website.',
    },
}
