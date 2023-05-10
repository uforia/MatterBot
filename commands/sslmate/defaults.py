#!/usr/bin/env python3

BINDS = ['@sslmate', '@ioc']
CHANS = ['debug']
APIURL = {
    'sslmate':  {'url': 'https://api.certspotter.com/v1/issuances?domain=',
                'key': '<your-API-key-here>'},
}
CONTENTTYPE = 'application/json'
EXPANDFIELDS = (
    'dns_names',
    'issuer.friendly_name',
    'issuer.caa_domains',
)
HELP = {
    'DEFAULT': {
        'args': '<domain> or <url>',
        'desc': 'Query the SSLMate Certificate Transparency logs for the given domain name (or URL).',
    },
}
