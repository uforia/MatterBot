#!/usr/bin/env python3

BINDS = ['@shodan', '@ioc']
CHANS = ['debug']
APIURL = {
    'shodan':   {'url': 'https://api.shodan.io',
                 'key': ['<your-api-key-here>','<another-api-key>','<yet-another-...>']},
}
CONTENTTYPE = 'application/json'

# Note: if you use multiple Shodan API keys to circumvent their API usage restrictions,
# you're probably breaking Shodan's terms of service. You're on your own.
