#!/usr/bin/env python3

BINDS = ['@docgen']
CHANS = ['debug']
CONTENTTYPE = 'application/json'
APIURL = {
    'docgen':   {
        'url': '<your WikiJS instance\'s URL here>',
        'key': '<your WikiJS\' API token here>',
    },
}
HELP = {
    'DEFAULT': {
        'args': '<type> <name> <arg1> <arg2> ... <arg#>',
        'desc': 'Create a composite `type` document for `name` from the given WikiJS pages.',
    },
}