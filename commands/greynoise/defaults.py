#!/usr/bin/env python3

BINDS = ['@greynoise']
CHANS = ['debug']
APIURL = {
    'greynoise':   {'url': 'https://api.greynoise.io',
                 'key': ['<your-api-key-here>','<another-api-key>','<yet-another-...>']}, # You need at least a free account!
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Query the GreyNoise API for various types of information. This module '
                'will include a valid JSON response from GreyNoise as a file upload, so '
                'you can reuse the information and do not need to repeat queries.',
    },
    'ip': {
        'args': '<ip address>',
        'desc': 'Do a GreyNoise IP lookup.',
    },
}

# Note: if you use multiple GreyNoise API keys to circumvent their API usage restrictions,
# you might be breaking GreyNoise's terms of service. You're on your own.
