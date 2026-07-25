#!/usr/bin/env python3

BINDS = ['@abuseipdb', '@ioc']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
# A netblock (a.b.c.d/n) is queried via the check-block endpoint, a single address via check.
ACCEPTS = ['ip', 'ipv6', 'cidr']
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
