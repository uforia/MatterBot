#!/usr/bin/env python3

BINDS = ['@iplocation', '@il', '@geo', '@geolookup']
CHANS = ['debug']
APIURL = {
    'iplocation':    {'url': 'https://api.iplocation.net/?ip='},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IP Address>',
        'desc': 'Returns the IP location, if available.',
    },
}
