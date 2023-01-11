#!/usr/bin/env python3

BINDS = ['@shodan']
CHANS = ['debug']
APIURL = {
    'shodan':   {'url': 'https://api.shodan.io',
                 'key': ['<your-api-key-here>','<another-api-key>','<yet-another-...>']},
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': None,
        'desc': 'Query the Shodan API for various types of information.',
    },
    'ip': {
        'args': '<ip address>',
        'desc': 'Do a Shodan IP lookup.',
    },
    'host': {
        'args': '<hostname>',
        'desc': 'Do a Shodan Host lookup.',
    },
    'count': {
        'args': 'query:<text1,text2,...> [filters:<...,...>] [facets:<...,...>] ',
        'desc': 'The provided `text#N` fields are used to search the database of banners in Shodan, '
                'with additional options for filters and facets inside the search query using a '
                '`type:value` format for every `filter#N` entry and a list of facets in a `facets:'
                'facet#1,facet#2,...` format. E.g.: this search query would find Apache Web servers '
                'located in Germany: `apache filters:country:DE`.\n'
                'This search does not return any host results; it only returns the '
                'total number of results that matched the query and any facet information that was '
                'requested. As a result, this method does not consume query credits.\n'
                'List of Shodan filters: [Shodan filters](https://beta.shodan.io/search/filters)\n'
                'List of Shodan facets: [Shodan facets](https://beta.shodan.io/search/facet)',
    },
    'credits': {
        'args': None,
        'desc': 'Display the Shodan account credits and status.',
    },
}

# Note: if you use multiple Shodan API keys to circumvent their API usage restrictions,
# you're probably breaking Shodan's terms of service. You're on your own.
