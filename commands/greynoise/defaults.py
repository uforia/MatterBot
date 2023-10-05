#!/usr/bin/env python3

BINDS = ['@greynoise']
CHANS = ['debug']
APIURL = {
    'greynoise':   {'url': 'https://api.greynoise.io',
                 'key': ['<your-api-key-here>','<another-api-key>','<yet-another-...>']}, # You need at least a free account!
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Query the greynoise API for various types of information. This module '
                'will include a valid JSON response from greynoise as a file upload, so '
                'you can reuse the information and do not need to repeat queries.',
    },
    'ip': {
        'args': '<ip address>',
        'desc': 'Do a greynoise IP lookup.',
    },
    'host': {
        'args': '<hostname>',
        'desc': 'Do a greynoise Host lookup.',
    },
    'credits': {
        'args': None,
        'desc': 'Display the greynoise account credits and status.',
    },
    'account': {
        'args': None,
        'desc': 'Display the greynoise account credits and status.',
    },
    'count': {
        'args': 'query:<word1,word2,...> [filters:<...,...>] [facets:<...,...>] ',
        'desc': 'The provided `word#N` fields are used to search the database of banners in greynoise, '
                'with additional options for filters and facets inside the search query using a '
                '`type:value` format for every `filter#N` entry and a list of facets in a `facets:'
                'facet#1,facet#2,...` format. Replace spaces with a comma. For example, '
                '`... count query:cobalt,strike filters:country:DE facets:org` would count '
                'the number of Cobalt Strike beacons in Germany, grouped by `organization`.\n'
                'This search does not return any host results; it only returns the '
                'total number of results that matched the query and any facet information that was '
                'requested. As a result, this method does not consume query credits.\n'
                'List of greynoise filters: [greynoise filters](https://beta.greynoise.io/search/filters)\n'
                'List of greynoise facets: [greynoise facets](https://beta.greynoise.io/search/facet)',
    },
    'search': {
        'args': 'query:<text1,text2,...> [filters:<...,...>] [facets:<...,...>] [limit:<#>]',
        'desc': 'The provided `text#N` fields are used to search the database of banners in greynoise, '
                'with additional options for filters and facets inside the search query using a '
                '`type:value` format for every `filter#N` entry and a list of facets in a `facets:'
                'facet#1,facet#2,...` format. Replace spaces with a comma. For example, '
                '`... search query:cobalt,strike filters:country:NL limit:200` would return the '
                'first 200 Cobalt Strike beacons in the Netherlands.\n'
                'This search returns detailed host results and consumes credits. Every 100 results '
                '(every greynoise \'page\') beyond the first will cost 1 credit.\n'
                'List of greynoise filters: [greynoise filters](https://beta.greynoise.io/search/filters)\n'
                'List of greynoise facets: [greynoise facets](https://beta.greynoise.io/search/facet)\n'
                'Default `limit` setting: `100` results (meaning: first page only)',
    },
}

# Note: if you use multiple GreyNoise API keys to circumvent their API usage restrictions,
# you might be breaking GreyNoise's terms of service. You're on your own.
