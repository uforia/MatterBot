#!/usr/bin/env python3

BINDS = ['@asnwhois', '@asn']
CHANS = ['debug']
APIURL = {
    'asnwhois':   {'url': 'https://api.asrank.caida.org/v2/restful/asns/'},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<ASN>',
        'desc': 'Returns the ASN and geolocation, if available.',
    },
}
