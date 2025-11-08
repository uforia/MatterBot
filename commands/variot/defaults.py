#!/usr/bin/env python3

BINDS = ['@variot', '@vi', '@ioc']
CHANS = ['debug']
APIURL = {
    'variot':
        {
            'url': 'https://www.variotdbs.pl/api/',
            'key': None, # Consider signing up to be able to do mome than 100 queries per day
        },
}
CONTENTTYPE = 'application/json'
LIMIT = 10
HELP = {
    'DEFAULT': {
        'args': '<exploit>, <search> or <vuln>',
        'desc': 'Search the VARIoT database for text or query it for information on a vulnerability '
                'or exploit. VAR Vulnerability and Exploit Identifiers are formatted as `VAR-YEARMONTH-ENUMERATOR` '
                'or `VAR-E-YEARMONTH-ENUMERATOR.',
    },
    'search': {
        'args': '<text> [limit:<limit>]',
        'desc': 'Search the VARIoT database for the given text and return all known vulnerabilities and '
                'exploits. The last `%s` results are returned by default, but this can be overridden '
                'with the `limit:##` option. Be warned that some searches can return tens of thousands '
                'of results. A JSON file is returned with each query for further processing.' % LIMIT,
    },
    'vuln': {
        'args': '<VAR ID>',
        'desc': 'Display information for the vulnerability with the given ID, e.g. `vuln VAR-201810-002`.',
    },
    'exploit': {
        'args': '<VAR-E ID>',
        'desc': 'Display information for the exploit with the given ID, e.g. `VAR-E-202403-0059`.',
    },
}
