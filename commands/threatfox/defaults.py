#!/usr/bin/env python3

BINDS = ['@threatfox', '@ioc', '@tf']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
# IPv4 only -- the module validates with a v4 regex and does not handle IPv6.
ACCEPTS = ['ip', 'md5', 'sha1', 'sha256']
CHANS = ['debug']
APIURL = {
    'threatfox':   {
        'url': 'https://threatfox-api.abuse.ch/api/v1/',
        'key': '<your-threatfox-api-key-here>',
        },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IP address|MD5|SHA1|SHA256>',
        'desc': 'Query ThreatFox for the given IP address or file hash, and display threat, tags and reference(s).',
    },
}
