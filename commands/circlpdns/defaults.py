#!/usr/bin/env python3

BINDS = ['@circlpdns', '@cpdns', '@ioc']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
ACCEPTS = ['ip', 'ipv6', 'cidr', 'domain']
# Offer this module to the AI analyst as a tool (see the AI: block in the config).
# Read-only and opt-in; withdraw it with AITOOL = False in settings.py, or centrally
# via AI.blocked_modules.
AITOOL = True
CHANS = ['debug']
APIURL = {
    'circlpdns': {
        'url': 'https://www.circl.lu/pdns/query/',
        'user': '<your-circl-pdns-username>',
        'key': '<your-circl-pdns-password>',
    },
}
CONTENTTYPE = 'application/json'
MAX_ROWS = 50
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<domain|IP|CIDR>',
        'desc': 'Query CIRCL Passive DNS for records observed for a domain, IPv4/IPv6 address, or CIDR network. Requires a CIRCL pDNS account (https://www.circl.lu/services/passive-dns/).',
    },
}
