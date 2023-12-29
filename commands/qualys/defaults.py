#!/usr/bin/env python3

BINDS = ['@qualys', '@ql']
CHANS = ['debug']
APIURL = {
    'qualys':   {
        'jwt':  'https://gateway.qg1.apps.qualys.eu/auth',
        'csam': 'https://gateway.qg1.apps.qualys.com/rest/2.0/',
        'username': '<your-username>',
        'password': '<your-password>',
    },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<domain|host|ip|software|sw|search>',
        'desc': 'Query your company\'s Qualys SAAS solution for information about assets and vulnerabilities.`.',
    },
    'domain': {
        'args': '<Domain>',
        'desc': 'Search through the Qualys database for all assets that contain the given (partial) domain name, '
                'e.g. `... domain kpn.com`. This can generate a lot of output, be as specific as possible!',
    },
    'host': {
        'args': '<Hostname>',
        'desc': 'Look up all Qualys information for a specific hostname, e.g. `... host srv01.example.com`',
    },
    'ip': {
        'args': '<IP Address>',
        'desc': 'Look up all Qualys information for a specific IP address, e.g. `... ip 10.0.0.4`',
    },
    'software': {
        'args': '<String>',
        'desc': 'Search through the Qualys database for all assets running <software>, e.g. `... software apache`. '
                'This can generate a lot of output, be as specific as possible!',
    },
    'sw': {
        'args': '<String>',
        'desc': 'Search through the Qualys database for all assets running <software>, e.g. `... software apache`. '
                'This can generate a lot of output, be as specific as possible. This command is short-hand for the '
                '`software` command.',
    },
}
