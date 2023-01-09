#!/usr/bin/env python3

BINDS = ['@virustotal', '@ioc', '@vt']
CHANS = ['debug']
APIURL = {
    'virustotal':   {'url': 'https://www.virustotal.com/api/v3/',
                     'key': ['<your-api-key-here>','<another-api-key>','<yet-another-...>']},
    'malpedia':     {'url': 'https://malpedia.caad.fkie.fraunhofer.de/api/get/yara',
                     'key': '<your-api-key-here>',
                     'enabled': True},
}
CONTENTTYPE = 'application/json'

# Note: if you use multiple VirusTotal API keys to circumvent their API usage restrictions,
# you're breaking VT's terms of service. You're on your own.

# Enable the Malpedia settings to attempt to automatically grab accompanying YARA rulesets
# when you look up an IoC. You need a valid API key to be able to do this, in some cases.
