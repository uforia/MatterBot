#!/usr/bin/env python3

BINDS = ['@dnsdumpster', '@dns']
CHANS = ['debug']
APIURL = {
    'dnsdumpster': {
        'url': 'https://api.dnsdumpster.com/domain/',
        'key': '<your-api-key-here>'
        }

}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<domain> <record type>',
        'desc': 'Returns DNS information related to a Domain. Example query is `@dnsdumpster domain.com`.'
                ' Optionally you can specify specific record types eg. `@dnsdumpster domain.com a, mx`.'
                ' If no records types are specified, all records types are requested',
    },
}
