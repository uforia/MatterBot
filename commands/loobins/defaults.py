#!/usr/bin/env python3

BINDS = ['@loobins', '@lb', '@ioc']
CHANS = ['debug']
APIURL = {
    'loobins':   {'url': 'https://www.loobins.io/loobins.json'},
}
CONTENTTYPE = 'application/json'
CACHE = 'commands/loobins/loobins.json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Search LOOBINS (Living-Off-the-Orchard binaries, MacOS X) for information and return any matching entries, '
                'matching on filenames, description and paths. On its first run, the module will build a cache of the '
                'LOOBINS website, so the very first query will be slow.',
    },
    'rebuildcache': {
        'args': None,
        'desc': 'Force a rebuild of the cache. Please use this sparingly and do not overload the LOOBINS website.',
    },
}
