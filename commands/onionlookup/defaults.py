#!/usr/bin/env python3

BINDS = ['@onionlookup', '@ioc', '@ol']
CHANS = ['debug']
APIURL = {
    'onionlookup':  {
        'url': 'https://onion.ail-project.org/api/lookup/',
    },
}
CONTENTTYPE = 'text/html'
HELP = {
    'DEFAULT': {
        'args': '<URL>',
        'desc': 'Query the CIRCL Onion-Lookup API for the given URL and display the known metadata.',
    },
}
