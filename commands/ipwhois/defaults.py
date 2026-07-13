#!/usr/bin/env python3

BINDS = ['@ipwhois', '@ioc']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
# IPv4 only -- the module validates with a v4 regex and does not handle IPv6.
ACCEPTS = ['ip']
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
