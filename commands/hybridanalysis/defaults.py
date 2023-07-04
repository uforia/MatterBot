#!/usr/bin/env python3

BINDS = ['@hybridanalysis', '@ha']
CHANS = ['debug']
APIURL = {
    'hybridanalysis':   {'url': 'https://www.hybrid-analysis.com/api/v2/',
                         'key': '<your-api-key>',
                         'secret': '<your-api-secret>'},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IPv4|IPv6|domain|hostname|md5|sha1|sha256|url',
        'desc': 'Query the Hybrid-Analysis API for various types of information.',
    },
}
