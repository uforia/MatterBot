#!/usr/bin/env python3

BINDS = ['@haveibeenpwnd', '@hibp']
CHANS = ['debug']
APIURL = {
    'hibp_email':   {'url': 'https://haveibeenpwned.com/api/v3/breachedaccount/'},
    'hibp_domain':  {'url': 'https://haveibeenpwned.com/api/v3/breacheddomain/'},
    'hibp_breach':  {'url': 'https://haveibeenpwned.com/api/v2/breach/'},
    'hibp':         {'key': 'your api key'}
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<searchtype email|breach|domain>, <search value>',
        'desc': 'Option `email` returns all breaches for a email adress, option `breach` returns info related to a breach, and option `domain` returns all breached accounts within a domain. Example query for querying breaches for an email is "@hibp email testuser@gmail.com". Example query for searching a breach is "@hibp breach adobe"',
    },
}

