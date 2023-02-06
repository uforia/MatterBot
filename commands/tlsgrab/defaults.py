#!/usr/bin/env python3

BINDS = ['@tlsgrab', '@tg']
CHANS = ['debug']
HELP = {
    'DEFAULT': {
        'args': '<IP address>[:optional port], e.g.: `127.0.0.1:443`',
        'desc': 'Connect to the specified IP address and retrieve its SSL/TLS certificate information, if available.',
    },
}
