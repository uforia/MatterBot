#!/usr/bin/env python3

BINDS = ['@urlhaus', '@ioc', '@uh']
CHANS = ['debug']
APIURL = {
    'urlhaus':  {'url': 'https://urlhaus-api.abuse.ch/v1/url/', 'payload': 'https://urlhaus-api.abuse.ch/v1/payload/'},
}
CONTENTTYPE = 'text/html'
HELP = {
    'DEFAULT': {
        'args': '<MD5|SHA1|SHA256|URL>',
        'desc': 'Query URLhaus for the given IoC and display threat, host, payload(s), tags, status and reference(s).',
    },
}
