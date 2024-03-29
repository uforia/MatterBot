#!/usr/bin/env python3

BINDS = ['@geo', '@geolookup', '@gl']
CHANS = ['debug']
APIURL = {
    'osmdata':    {'url': 'https://nominatim.openstreetmap.org/reverse?'},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<latitude> <longitude>',
        'desc': 'Returns the geolocation, if available.',
    },
}
