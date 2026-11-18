#!/usr/bin/env python3

BINDS = ['@vpndetection', '@vpnd']
CHANS = ['debug']
APIURL = {
    'vpndetection':
        {
            'url': 'https://api.vpndetection.io/',
            'key': None, # Not needed: lookups are free and unlimited without a key (https://vpndetection.io/terms#no-key)
        },
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<IP address>',
        'desc': 'Query the VPNDetection API for whether an IP address is a VPN, Tor exit node or privacy relay, with its network and location. Example query is `@vpndetection 185.220.101.1`',
    },
}
