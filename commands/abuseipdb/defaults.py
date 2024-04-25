#!/usr/bin/env python3

BINDS = ['@abuseipdb', '@ioc']
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
