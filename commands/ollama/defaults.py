#!/usr/bin/env python3

BINDS = ['@ol', '@ollama']
CHANS = ['debug']
APIENDPOINT = '<your-ollama-instance>'
CONTENTTYPE = 'application/json'
MODEL = '<choose-your-model>'
TEMPERATURE = 0.9
HELP = {
    'DEFAULT': {
        'args': '<question|request|instruction>',
        'desc': 'Sends your request to an Ollama instance and returns the answer. Answers may take some time, so please be patient and use this module sparingly!',
    },
}
