#!/usr/bin/env python3

BINDS = ['@ipwhois', '@ioc']
CHANS = ['debug']
APIURL = {
    'ipwhois':   {'url': 'https://ipwho.is/'},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IP address>',
        'desc': 'Returns the IPWHOIS ISP, ASN and geolocation information for the given IP address.',
    },
}
