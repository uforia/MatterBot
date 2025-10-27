#!/usr/bin/env python3

BINDS = ['@euvd']
CHANS = ['debug']
APIURL = {
    'euvd':
        {
            'url': 'https://euvdservices.enisa.europa.eu/api/',
        },
}
CONTENTTYPE = 'application/json'
SEVERITIES = {
    'low': 4.0,
    'medium': 7.0,
    'high': 9.0,
    'critical': 10,
}
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Query the EUVD API for various types of information. This module '
                'will include a valid JSON response for CVE details. Possible subcommands '
                'are `search`, `cve`.',
    },
    'search': {
        'args': '<keyword1,keyword2,...,keyword#> [cvss:<low,medium,high,critical>]',
        'desc': 'Search through the EUVD database for vulnerabilities that include '
                'all of <keyword1>, <keyword2>, etc., optionally limiting the search '
                'by CVSS severity. If there are more than 10 results, the 10 most '
                'recently updated CVEs will be displayed, and the complete result set '
                'will be included as a CSV download.',
    },
    'euvd': {
        'args': '<EUVD ID>',
        'desc': 'Grab the detailed description for the given EUVD-ID. Output will '
                'include a JSON download.',
    },
}

# Note: if you use the public EUVD API, you may end up being blocked if you overuse
# the API or otherwise hit the rate limits.
