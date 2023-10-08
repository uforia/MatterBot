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
        'desc': 'Query the GreyNoise API for various types of information. This module '
                'may include a valid JSON response from GreyNoise as a file upload, so '
                'you can reuse the information and do not need to repeat queries. Available '
                'query types are: `<community|ipcontext|ipquick|riot|gnql|gqnlstats|timeline'
                '|similarity|ping>`. Not all query types may be available for your account '
                'type, and most will consume API key credits.',
    },
    'community': {
        'args': '<ip address>',
        'desc': 'Do a GreyNoise Community IP lookup. This is the default behaviour.',
    },
    'ipcontext': {
        'args': '<ip address>',
        'desc': 'Do a GreyNoise IP Context lookup. Returns the most extensive information available '
                'about a given IP, such as times seen, actor, classification, VPN/TOR information '
                'ASN, operating system, source/destination countries, paths and ports scanned, and '
                'fingerprint information, if available.',
    },
    'ipquick': {
        'args': '<ip address>',
        'desc': 'Do a GreyNoise quick IP lookup. This will indicate whether or not the GreyNoise '
                'network considers the IP address as noise and/or if it is considered benign as '
                'per the RIOT database.',
    },
    'riot': {
        'args': '<ip address>',
        'desc': 'Do a GreyNoise RIOT IP lookup. This checks whether GreyNoise considers the IP '
                'benign or not.',
    },
    'gnql': {
        'args': '<ip address>',
        'desc': 'Not yet implemented.',
    },
    'gnqlstats': {
        'args': '<ip address>',
        'desc': 'Not yet implemented.',
    },
    'timeline': {
        'args': '<daily|hourly|field> <ip address>',
        'desc': 'Create a GreyNoise timeline for a given IP. Example: `<..> daily:days:7,cursor:'
                'cafebabe,limit:30 <ip>` to create a timeline for `<ip>`, for the past `7` days, '
                'starting at cursor position `cafebabe`. The field names are `days`, `cursor` and '
                '`limit` for `daily` and `hourly` lookups, for `field` lookups they are `days`, '
                '`field` and `granularity`. Valid `Field` values are `destination_port`, `http_path`, '
                '`http_user_agent`, `source_asn`, `source_org`, `source_rdns`, `tag_ids` and '
                '`classification`. `Granularity` is the granularity activity date ranges, e.g. `1d` '
                'or `7h`. For a comprehensive explanation, refer to [https://docs.greynoise.io/reference/get_v3-noise-ips-ip-timeline]'
                '(the official GreyNoise API documentation). Please note that this feature requires '
                'an additional subscription license and may not work for you.',
    },
    'similarity': {
        'args': '<ip address>',
        'desc': 'Do a GreyNoise IP similarity lookup. This checks whether GreyNoise has seen other '
                'IP addresses exhibiting matching scanning features. Returned information includes '
                'whether the IP is known as a TOR/VPN exit node, part of a bot network, user-agents '
                'fingerprints (such as SSL/TLS and SSH), ports scanned, operating system and more. '
                'Please note that this feature requires an additional subscription license and may '
                'not work for you.',
    },
}

# Note: if you use multiple GreyNoise API keys to circumvent their API usage restrictions,
# you might be breaking GreyNoise's terms of service. You're on your own.
