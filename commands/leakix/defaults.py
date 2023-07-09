#!/usr/bin/env python3

BINDS = ['@leakix', '@li']
CHANS = ['debug']
# Note: if you use multiple API keys and you get banned, it's your own fault.
APIURL = {
    'leakix':   {'url': 'https://leakix.net/',
                 'key': ['<your-api-key>',]},
}
CONTENTTYPE = 'application/json'
LEAKLIMIT = 10
HELP = {
    'DEFAULT': {
        'args': '<domain|hostname|subdomains',
        'desc': 'Query the LeakIX API for various types of information.',
    },
}
