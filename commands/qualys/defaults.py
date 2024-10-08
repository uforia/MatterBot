#!/usr/bin/env python3

BINDS = ['@qualys', '@ql']
CHANS = ['debug']
APIURL = {
    'qualys':   {
        'jwt':  'https://gateway.qg1.apps.qualys.eu/auth',
        'am': 'https://gateway.qg1.apps.qualys.com/rest/2.0/',
        'username': '<your-username>',
        'password': '<your-password>',
    },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<domain|host|ip|software|sw|search>',
        'desc': 'Query your company\'s Qualys SAAS solution for information about assets and vulnerabilities.',
    },
    'domain': {
        'args': '<domain>',
        'desc': 'Search through the Qualys database for all assets that contain the given (partial) domain name, '
                'e.g. `... domain kpn.com`. This can generate a lot of output, be as specific as possible!',
    },
    'host': {
        'args': '<hostname>',
        'desc': 'Look up all Qualys information for a specific hostname, e.g. `... host srv01.example.com`',
    },
    'ip': {
        'args': '<IP address>',
        'desc': 'Look up all Qualys information for a specific IP address, e.g. `... ip 10.0.0.4`',
    },
    'publisher': {
        'args': '<string>',
        'desc': 'This is an alias for the `software` query.'
    },
    'software': {
        'args': '<string>',
        'desc': 'Search through the Qualys database for all assets running <software>, e.g. `... software apache`. '
                'Please be aware that this potentially is a very time-intensive lookup (several minutes). Try be as specific as possible!',
    },
    'sw': {
        'args': '<string>',
        'desc': 'This is an alias for the `software` query.'
    },
}
