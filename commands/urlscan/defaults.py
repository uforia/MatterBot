#!/usr/bin/env python3

BINDS = ['@urlscan', '@us', '@ioc']
CHANS = ['debug']
APIURL = {
    'urlscan':   {
        'url': 'https://urlscan.io/api/v1/search',
        'key': '<your-urlscan-api-key-here>',
        },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IP address|Domain|Hostname|URL|SHA256>',
        'desc': 'Query Urlscan for the given IP address, domain, hostname, URL or hash.',
    },
}
ENTRIES = 10