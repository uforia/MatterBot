#!/usr/bin/env python3

BINDS = ['@analyze']
CHANS = ['debug']
# You can change the 'month' part of the APIURL to a different timeframe, if so desired.
CONTENTTYPE = 'application/json'
# List of Matterbot modules that should be called. Never include your BINDS in here, or you
# can potentially loop the bot!
AUTOEXEC = [
    '@ioc',
]
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'The bot will automatically download your attachment and calculate common hashes, '
                'after which it will automatically the run the `'+'`'.join(AUTOEXEC)+'` commands '
                'with the resulting values. This can be used to automate the parsing of interesting '
                'files',
    },
}