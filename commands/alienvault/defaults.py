#!/usr/bin/env python3

BINDS = ['@alienvault', '@av']
CHANS = ['debug']
APIURL = {
    'alienvault':   {'url': 'https://otx.alienvault.com/api/v1/indicators/',
                     'key': '<your-api-key>'},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IPv4|IPv6|domain|hostname|md5|sha1|sha256|url',
        'desc': 'Query the AlienVault OTX API for various types of information. This module '
                'will include a valid JSON response from AlienVault OTX as a file upload, so '
                'you can reuse the information and do not need to repeat queries.',
    },
}
