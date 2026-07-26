#!/usr/bin/env python3

BINDS = ['@ipinfo', '@ip', '@ioc']
CHANS = ['debug']
APIURL = {
    'ipinfo':   {'url': 'https://ipinfo.io/',
                 'key': '<your-token>'}

}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<ip adress>',
        'desc': 'Returns IPinfo information related to an IP. This also includes the ASN, which can then be queried using the asnwhois plugin. Example query is `@ipinfo 8.8.8.8`',
    },
}
