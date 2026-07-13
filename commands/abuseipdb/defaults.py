#!/usr/bin/env python3

BINDS = ['@abuseipdb', '@ioc']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
# A netblock (a.b.c.d/n) is queried via the check-block endpoint, a single address via check.
ACCEPTS = ['ip', 'ipv6', 'cidr']
# Offer this module to the AI analyst as a tool (see the AI: block in the config).
# Read-only and opt-in; withdraw it with AITOOL = False in settings.py, or centrally
# via AI.blocked_modules.
AITOOL = True
CHANS = ['debug']
APIURL = {
    'abuseipdb':   {
        'url': 'https://api.abuseipdb.com/api/v2/',
        'key': None,
    },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IP address> or <netblock>',
        'desc': 'Query AbuseIPDB for the IP address/netblock and display the results, such as its reputation, usage and abuse confidence score.',
    },
}
