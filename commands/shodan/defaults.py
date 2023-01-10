#!/usr/bin/env python3

BINDS = ['@shodan', '@ioc']
CHANS = ['debug']
APIURL = {
    'shodan':   {'url': 'https://api.shodan.io',
                 'key': ['<your-api-key-here>','<another-api-key>','<yet-another-...>']},
}
CONTENTTYPE = 'application/json'

# Note: if you use multiple VirusTotal API keys to circumvent their API usage restrictions,
# you're breaking VT's terms of service. You're on your own.

# Enable the Malpedia settings to attempt to automatically grab accompanying YARA rulesets
# when you look up an IoC. You need a valid API key to be able to do this, in some cases.
