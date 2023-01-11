#!/usr/bin/env python3

BINDS = ['@abusech', '@ioc']
CHANS = ['debug']
APIURL = {
    'threatfox':   {'url': 'https://threatfox-api.abuse.ch/api/v1/'},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IP address|MD5|SHA1|SHA256>',
        'desc': 'Query ThreatFox for the given IP address or file hash, and display threat, tags and reference(s).',
    },
}
