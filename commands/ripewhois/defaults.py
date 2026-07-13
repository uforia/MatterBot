#!/usr/bin/env python3

BINDS = ['@ripewhois', '@ioc']
# Indicator types this module accepts under a shared bind like @ioc (see cmdutils.accepts).
# IPv4 only -- the module validates with a v4 regex and does not handle IPv6.
ACCEPTS = ['ip']
CHANS = ['debug']
APIURL = {
    'ripewhois':   {'url': 'https://stat.ripe.net/data/whois/data.json?resource='},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IP address>',
        'desc': 'Query RIPE WHOIS for the IP address and display the ranges, orgs, countries and geolocation.',
    },
}
