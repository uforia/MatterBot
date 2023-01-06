#!/usr/bin/env python3

BINDS = ['@malpedia', '@ioc', '@mp']
CHANS = ['debug']
APIURL = {
    'malpedia':   {'url': 'https://malpedia.caad.fkie.fraunhofer.de/api/',
                   'key': '<your-api-key-here>'},
    'mitre':      {'url': 'http://149.210.137.179:8008/api/explore/',
                   'key': None},
}
CONTENTTYPE = 'application/json'
