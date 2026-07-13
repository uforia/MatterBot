#!/usr/bin/env python3

BINDS = ['@urlhaus', '@ioc', '@uh']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
ACCEPTS = ['md5', 'sha1', 'sha256', 'url']
# Offer this module to the AI analyst as a tool (see the AI: block in the config).
# Read-only and opt-in; withdraw it with AITOOL = False in settings.py, or centrally
# via AI.blocked_modules.
AITOOL = True
CHANS = ['debug']
APIURL = {
    'urlhaus':  {
        'url': 'https://urlhaus-api.abuse.ch/v1/url/',
        'payload': 'https://urlhaus-api.abuse.ch/v1/payload/',
        'key': '<your-urlhaus-api-key-here>',
    },
}
CONTENTTYPE = 'text/html'
HELP = {
    'DEFAULT': {
        'args': '<MD5|SHA1|SHA256|URL>',
        'desc': 'Query URLhaus for the given IoC and display threat, host, payload(s), tags, status and reference(s).',
    },
}
