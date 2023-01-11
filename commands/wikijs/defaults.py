#!/usr/bin/env python3

BINDS = ['@wiki', '@wikijs']
CHANS = ['debug']
WIKIURL = '<your-wikijs-webaddress-for-linking>'
APIENDPOINT = '<your-Microsoft-Azure-Cloud-Search-url>'
INDEX = '<Azure Cloud Search Index name>'
CONTENTTYPE = 'application/json'
APIKEY = '<your-API-key>'
HELP = {
    'DEFAULT': {
        'args': '<search terms/text>',
        'desc': 'Query your WikiJS instance for the given search terms/text and list pages where they were found.',
    },
}
