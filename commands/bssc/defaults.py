#!/usr/bin/env python3

BINDS = ['@bssc', '@ioc']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
ACCEPTS = ['ip', 'domain', 'url', 'sha256']
CHANS = ['debug']
APIURL = {
    'bssc':   {'url': 'https://api.sep.securitycloud.symantec.com/v1/threat-intel/insight',
               'token': 'https://api.sep.securitycloud.symantec.com/v1/oauth2/tokens',
               'key': '<your-API-key-here>'},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<SHA256>, <IP address>, <domain> or <URL>',
        'desc': 'Query the Broadcom Symantic Security Cloud for the given file hash, IP address, domain name or URL.',
    },
}
