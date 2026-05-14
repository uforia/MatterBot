#!/usr/bin/env python3

BINDS = ['@wigle', '@wg']
CHANS = ['debug']
APIURL = {
    'wigle': {
        # WiGLE — wireless-network geolocation (https://wigle.net/).
        # Free registration. Auth is HTTP Basic with API NAME + API TOKEN.
        # Both are required (a single composite key won't work).
        'url': 'https://api.wigle.net/api/v2/',
        'name':  '<your-wigle-api-name-here>',
        'token': '<your-wigle-api-token-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_RESULTS = 8
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '[ssid|bssid] <value>',
        'desc': (
            'WiGLE wireless-network lookup. `ssid <name>` searches by '
            'network name (substring match); `bssid <MAC>` looks up a '
            'specific access point by MAC. Bare `@wigle <value>` auto-routes '
            'MAC-shaped input to bssid, anything else to ssid. Requires a '
            'free WiGLE account (https://wigle.net/).'
        ),
    },
}
