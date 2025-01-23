#!/usr/bin/env python3

BINDS = ['@ai', '@llm']
CHANS = ['debug']
APIURL = {
    'llm':   {
        'url': '<your-llm-api-instance>',
        'key': '<your-api-key>',
    },
}
CONTENTTYPE = 'application/json'
# LLM-related settings, do not change unless needed
TEMP = 0.9
CL = 8192 # Max context length
L = 512 # Max length
