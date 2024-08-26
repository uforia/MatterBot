#!/usr/bin/env python3

BINDS = ['@misp', '@ioc']
CHANS = ['debug']
APIURL = '<your-MISP-instance>'
APIENDPOINT = '<your-MISP-instance>/attributes/restSearch'
APIKEY = '<your-API-key>'
CONTENTTYPE = 'application/json'
MAXHITS = 5
HELP = {
    'DEFAULT': {
        'args': '<IP address|Host|Domain|URL|Hash|...>',
        'desc': 'Performs a wildcard match on your MISP instance for the given IoC and lists the correlating MISP Event(s).',
    },
}
