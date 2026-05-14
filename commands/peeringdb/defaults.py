#!/usr/bin/env python3

BINDS = ['@peeringdb', '@pdb']
CHANS = ['debug']
APIURL = {
    'peeringdb': {
        # Read endpoints are unauthenticated and quota-light. `key` is left
        # configurable so operators can drop in a PeeringDB API key for
        # higher rate limits or to query private fields, but it's optional.
        'url': 'https://www.peeringdb.com/api/',
        'key': '',
    },
}
CONTENTTYPE = 'application/json'
MAX_IX = 10
MAX_FAC = 10
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<ASN | AS<number>>',
        'desc': 'Look up network info on PeeringDB for an autonomous system: organisation, network type, IRR AS-set, traffic estimate, IXPs and facilities. No auth required.',
    },
}
