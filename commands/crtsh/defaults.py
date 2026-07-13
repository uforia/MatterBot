#!/usr/bin/env python3

BINDS = ['@crtsh', '@cs', '@ioc']
# Indicator types this module can look up. Under a shared bind like @ioc, the
# dispatcher only runs the module when the argument matches -- so a hash or IP
# no longer reaches this domain-only Certificate Transparency lookup.
ACCEPTS = ['domain']
CHANS = ['debug']
APIURL = {
    'crtsh':   {'url': 'https://crt.sh/json?q='}
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<domain>',
        'desc': 'Returns the domains and subdomains related to a certificate. This is usefull to find hidden subdomains related to a website. Make sure you only add the domain and not www. or https://. Example query is `@cs abuse.ch`',
    },
}
ENTRIES = 10