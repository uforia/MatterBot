#!/usr/bin/env python3

BINDS = ['@lolbas', '@lb', '@ioc']
CHANS = ['debug']
APIURL = {
    'lolbas':   {'url': 'https://lolbas-project.github.io/api/lolbas.json'},
}
CONTENTTYPE = 'application/json'
CACHE = 'commands/lolbas/lolbas.json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Search LOLBAS for information and return any matching entries, such as hashes, filenames, etc. '
                'On its first run, the module will build a cache of the LOLBAS website, so the very first query will be '
                'slow.',
    },
    'rebuildcache': {
        'args': None,
        'desc': 'Force a rebuild of the cache. Please use this sparingly and do not overload the LOLBAS website.',
    },
}
