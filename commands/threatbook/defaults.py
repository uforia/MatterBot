#!/usr/bin/env python3

BINDS = ['@threatbook', '@tb', '@ioc']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
ACCEPTS = ['ip', 'ipv6', 'domain', 'md5', 'sha1', 'sha256']
CHANS = ['debug']
APIURL = {
    'threatbook': {
        # Community API base — supports /ip, /domain, /file endpoints.
        # Free tier requires registration at https://threatbook.io/.
        'url': 'https://api.threatbook.io/v1/community/',
        'key': '<your-threatbook-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_TAGS = 20
MAX_JUDGMENTS = 10
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<IP|domain|MD5|SHA1|SHA256>',
        'desc': 'Query ThreatBook community for IP, domain, or file-hash reputation (severity, judgments, tags). Requires a free ThreatBook account (https://threatbook.io/).',
    },
}
