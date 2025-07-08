#!/usr/bin/env python3

BINDS = ['@lolrmm', '@lr', '@ioc']
CHANS = ['debug']
APIURL = {
    'lolrmm':   {'url': 'https://lolrmm.io/api/rmm_tools.json'},
}
CONTENTTYPE = 'application/json'
CACHE = 'commands/lolrmm/lolrmm.json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Search LOLRMM for information and return any matching entries, such as filenames, domain names, registry paths, etc. '
                'On its first run, the module will build a cache of the LOLRMM website, so the very first query will be '
                'slow.',
    },
    'rebuildcache': {
        'args': None,
        'desc': 'Force a rebuild of the cache. Please use this sparingly and do not overload the LOLRMM website.',
    },
}
