#!/usr/bin/env python3

BINDS = ['@ds', '@docsearch']
CHANS = ['debug']
APIURL = {
    'docspell':   {
        'url': 'https://<your-docspell-hostname>/api/v1',
        'username': '<your-docspell-automation-username>',
        'password': '<your-docspell-automation-password>',
    },
}
NAME="Docspell"
# Number of pre- and postamble characters in highlights
PREAMBLE=200
POSTAMBLE=200
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<search> or <upload>',
        'desc': 'You can either <search> through the DMS\' user\'s collective or <upload> new content to it. If '
                'you do not specify the query type, <search> is assumed.',
    },
    'search': {
        'args': '<keyword1>, <keyword2> ... <keyword#>',
        'desc': 'Search through the DMS user\'s collective for the given keywords. Searches are performed '
                'exactly as if you were using the DMS\' Web UI, meaning parentheses, logical operators, etc. '
                'will work as intended.',
    },
    'upload': {
        'args': '<NONE>',
        'desc': 'Upload new content to the DMS. If in a supported format such as text, '
                'Office documents, PDFs, etc., the DMS will immediately process the new file and extract its '
                'contents.',
    },
}
