#!/usr/bin/env python3

BINDS = ['@triage', '@tr']
CHANS = ['debug']
APIURL = {
    'triage':   {
                    'url': 'https://private.tria.ge/api/v0/', # Set to https://tria.ge/api/v0/ for the public API
                    'key': None, # Set to your own key (required!)
                    'apilimit': 200, # Default max API limit
                    'limit': 1000, # Hard limit on number of results,
                },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<tria.ge search pattern>',
        'desc': 'Query the Triage API for various types of information. Searches somewhat follow the format as laid out by '
                'the [Tria.ge documentation](https://tria.ge/docs/cloud-api/search/#search-operators).\nTwo fields can be '
                'specified: `query:...` and `filter:...`.\n`query:` can be any of the type `MD5`, `SHA1`, `SHA256`, '
                '`SHA512`, `URL`, `IPv4`, `IPv6`, `Domain/Host`, or a `BTC/ETH/DASH/XMR` cryptocoin wallet string - the bot will auto-detect this. '
                '\nFor example: `query:5ff465afaabcbf0150d1a3ab2c2e74f3a4426467 filter:family:wannacry and from:2024-08-03 '
                'to:2024-08-06` will show all entries related to the given hash, matching the family and within the given timespan. ',
    },
}
