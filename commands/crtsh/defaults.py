#!/usr/bin/env python3

BINDS = ['@crtsh', '@cs', '@ioc']
CHANS = ['debug']
APIURL = {
    'crtsh':   {'url': 'https://crt.sh/json?q='}
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<domain>',
        'desc': 'Returns the domains and subdomains related to a certificate. This is usefull to find hidden subdomains related to a website. Make sure you only add the domain and not www. or https://. Example query is "@cs abuse.ch"',
    },
}
