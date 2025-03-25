#!/usr/bin/env python3

BINDS = ['@koboldcpp']
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
HELP = {
    'DEFAULT': {
        'args': '<prompt>',
        'desc': 'Ask the KoboldCPP LLM for a response to the specified `prompt`. Depending on the AI/LLM system load, responses may take a while - be patient and use this sparingly.',
    },
}
