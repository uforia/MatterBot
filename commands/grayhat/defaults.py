#!/usr/bin/env python3

BINDS = ['@grayhat', '@ioc']
CHANS = ['debug']
APIURL = {
    'grayhat': {
        'url': 'https://buckets.grayhatwarfare.com/api/v2/',
        'key': '<your-api-key-here>'
        }
    }
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '@grayhat <keyword1> \nOptional: <keyword2> <extension> <-excludekeyword1> eg. confidential pdf',
        'desc': 'Grayhat Warfare is a search engine for public (eg. AWS, AZ, GCP) buckets and their contents. '
                'The search engine provides various filters, including the ability to search for files containing specific keywords, excluding certain keywords, and searching by filename extensions.',
    },
}
