#!/usr/bin/env python3

BINDS = ['@proxycheck', '@pc']
CHANS = ['debug']
APIURL = {
    'proxycheck':
        {
            'url': 'https://proxycheck.io/v3/',
            'key': None, # Consider signing up for the free tier to be able to do momre queries per day
        },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Query the ProxyCheck API for an IP or email address.',
    },
}
