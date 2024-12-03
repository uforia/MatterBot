#!/usr/bin/env python3

BINDS = ['@a1000', '@a1k', '@reversinglabs', '@rl', '@ioc']
CHANS = ['debug']
APIURL = {
    'a1000':   {
        'url': 'https://a1000.reversinglabs.com/api/',
        'key': '<your-a1000-key-here>',
    },
    'ticloud': {
        'url': 'https://data.reversinglabs.com/api/',
        'username': '<your-TICloud-username-here>',
        'password': '<your-TICloud-password-here>',
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
