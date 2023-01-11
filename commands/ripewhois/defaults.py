#!/usr/bin/env python3

BINDS = ['@ripewhois', '@ioc']
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
