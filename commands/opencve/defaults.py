#!/usr/bin/env python3

BINDS = ['@opencve']
CHANS = ['debug']
APIURL = {
    'opencve':
        {
            'url': 'https://<your-OpenCVE-instance>/api',
            'username': '<your-OpenCVE-username>',
            'password': '<your-OpenCVE-password>',
        },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Query the OpenCVE API for various types of information. This module '
                'will include a valid JSON response for CVE details. Possible subcommands '
                'are `search`, `cve`.',
    },
    'search': {
        'args': '<keyword1,keyword2,...,keyword#> [cvss:<low,medium,high,critical>]',
        'desc': 'Search through the OpenCVE database for vulnerabilities that include '
                'all of <keyword1>, <keyword2>, etc., optionally limiting the search '
                'by CVSS severity. If there are more than 10 results, the 10 most '
                'recently updated CVEs will be displayed, and the complete result set '
                'will be included as a CSV download.',
    },
    'cve': {
        'args': '<CVE ID>',
        'desc': 'Grab the detailed description for the given CVE-ID.',
    },
}

# Note: if you use the public OpenCVE API, you may end up being blocked if you overuse
# the API or otherwise hit the rate limits. Features may also not work. It is highly
# recommended to install and use your own OpenCVE instance for this module.
