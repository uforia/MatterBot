#!/usr/bin/env python3

BINDS = ['@botscout']
CHANS = ['debug']
APIURL = {
    'botscout':
        {
            'url': 'https://botscout.com/test/?all=',
            'key': None, # Add your Botscout API key here, if you have one
        },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': 'An <IP address>, <email address> or <name>',
        'desc': 'Query the Botscout API for IP addresses, names and email addresses. '
                'This module will display all information returned from the API. ',
    },
}
