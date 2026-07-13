#!/usr/bin/env python3

BINDS = ['@malshare', '@ms', '@ioc']
# Indicator types this module can look up: file hashes only. Under a shared bind
# like @ioc, an IP or domain no longer reaches this hash-only malware lookup.
ACCEPTS = ['md5', 'sha1', 'sha256']
CHANS = ['debug']
APIURL = {
    'malshare': {
        # Free registration at https://malshare.com/. Key required; the
        # /api.php read endpoints are all keyed.
        'url': 'https://malshare.com/api.php',
        'key': '<your-malshare-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_SOURCES = 10
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<MD5|SHA1|SHA256>',
        'desc': 'Query MalShare for a sample by hash. Returns file type, hash family (md5/sha1/sha256/ssdeep), source URL(s), and date observed. Requires a free MalShare account (https://malshare.com/).',
    },
}
