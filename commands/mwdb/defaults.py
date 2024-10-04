#!/usr/bin/env python3

BINDS = ['@mwdb', '@ioc']
CHANS = ['debug']
APIURL = {
    'mwdb':   {
        'url': 'https://mwdb.cert.pl/api/',
        'key': None,
    },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<blob|hash|multi>',
        'desc': 'Query MWDB for a blob, hash or multi-lookup (logical AND on e.g. multiple hashes, configs, texts) and display the results.',
    },
    'blob': {
        'args': '<text>',
        'desc': 'Query MWDB for text blobs containing <text> (same as \'text\' mode).',
    },
    'hash': {
        'args': '<MD5|SHA1|SHA256|SSDEEP|...>',
        'desc': 'Query MWDB for objects matching the given hash. If available/relevant, a ZIP of the malware and config analysis will also be returned.',
    },
    'multi': {
        'args': '[<MD5>] [<SHA1>] [tag:<..>] [string] ...',
        'desc': 'Query MWDB for objects matching the given combination of parameters (\'multi-search\' mode).',
    },
}
