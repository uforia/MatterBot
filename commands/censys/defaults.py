#!/usr/bin/env python3

BINDS = ['@censys']
CHANS = ['debug']
APIURL = {
    'censys':   {'url': 'https://search.censys.io/api/v2',
                 'key': '<your-api-key-here>',
                 'secret': '<your-api-secret-here>'},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Query the Censys API for various types of information. This module '
                'will include a valid JSON response from Censys as a file upload, so '
                'you can reuse the information and do not need to repeat queries.',
    },
    'ip': {
        'args': '<ip address>',
        'desc': 'Do a Censys IP lookup and return everything that Censys knows about that host.',
    },
    'cert': {
        'args': '<sha256 fingerprint>',
        'desc': 'Do a Censys certificate lookup and return all hosts that are offering the certificate fingerprint.',
    },
    'credits': {
        'args': None,
        'desc': 'Display your Censys account information.',
    },
    'account': {
        'args': None,
        'desc': 'Display your Censys account information.',
    },
}
