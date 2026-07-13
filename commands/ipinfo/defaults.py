#!/usr/bin/env python3

BINDS = ['@ipinfo', '@ip', '@ioc']
# Indicator types this module can look up: IP addresses only. Under a shared bind
# like @ioc, a domain or hash no longer reaches this IP-geolocation lookup.
ACCEPTS = ['ip', 'ipv6']
# Offer this module to the AI analyst as a tool (see the AI: block in the config).
# Read-only and opt-in; withdraw it with AITOOL = False in settings.py, or centrally
# via AI.blocked_modules.
AITOOL = True
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
