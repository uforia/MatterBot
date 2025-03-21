#!/usr/bin/env python3

BINDS = ['@translate', '@argos']
CHANS = ['debug']

PACKAGES = 'https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json'
DEFAULT_LAN = 'en'

HELP = {
    'DEFAULT': {
        'args': '<source lan> <dest lan (optional)> <string to translate>',
        'desc': 'Argos Translate is a offline translation library. It uses OpenNMT for translations. To view available language use the `-h` flag. '
                'Argos takes a source language as argument and tries to translate that to the default language (`{DEFAULT_LAN}`) or specified language. '
                'Example usage: `@argos ja こんにちは` or `@argos en ja Hello`.',
    },
}
