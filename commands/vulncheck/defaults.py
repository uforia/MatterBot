#!/usr/bin/env python3

BINDS = ['@vulncheck', '@vc']
CHANS = ['debug']
APIURL = {
    'vulncheck': {
        # Free-tier "Community" data is included; register at
        # https://vulncheck.com/ for an API token.
        'url': 'https://api.vulncheck.com/v3/',
        'key': '<your-vulncheck-api-token-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_REFERENCES = 8
MAX_DESC_CHARS = 800
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<CVE-YYYY-NNNN+>',
        'desc': 'Query VulnCheck for CVE detail (description, CVSS, CWE, references) and known exploit count. Requires a free VulnCheck account (https://vulncheck.com/).',
    },
}
