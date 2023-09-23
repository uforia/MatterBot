#!/usr/bin/env python3

BINDS = ['@snow', '@snowplough', '@sp']
CHANS = ['debug']
APIURL = {
    'servicenow':   {'url': '<your-ServiceNow-endpoint>',
                     'username': '<username>',
                     'password': '<password>',
                     'queries': {
                         '<query1>': 'endpoint/one',
                         '<query2>': 'endpoint/two',
                     },
                    }
}
CONTENTTYPE = 'application/json'
