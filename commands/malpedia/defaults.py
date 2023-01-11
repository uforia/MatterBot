#!/usr/bin/env python3

BINDS = ['@malpedia', '@ioc', '@mp']
CHANS = ['debug']
APIURL = {
    'malpedia':   {'url': 'https://malpedia.caad.fkie.fraunhofer.de/api/',
                   'key': '<your-api-key-here>'},
    'mitre':      {'url': 'http://149.210.137.179:8008/api/explore/',
                   'key': None},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<MD5|SHA256 hash>, <actor name> or <malware family names>',
        'desc': 'Query Malpedia for the given file hash or wildcard search for the actor or family names. Display any information, such as TTPs, alternative names, etc. and include a malware sample (ZIP) if available.',
    },
}
