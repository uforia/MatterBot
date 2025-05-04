#!/usr/bin/env python3

BINDS = ['@macvendors', '@mac']
CHANS = ['debug']
APIURL = {
    'macvendors': {
        'url': 'https://api.macvendors.com/'
        }

}
HELP = {
    'DEFAULT': {
        'args': '<address>',
        'desc': 'Returns the vendor information related to a MAC Address. Example query is `@macvendors 00:11:22:33:44:55`.'
                ' Other formats such as `0011.2233.4455`, `00-11-22-33-44-55`, `001122334455` are also possible.',
    },
}
