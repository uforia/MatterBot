#!/usr/bin/env python3

BINDS = ['@openai', '@chatgpt']
CHANS = ['debug']
APIENDPOINT = 'https://api.openai.com/v1/completions'
CONTENTTYPE = 'application/json'
APIKEY = '<insert-key-here>'
MODEL = 'text-davinci-003'
TEMPERATURE = 0.9
MAX_TOKENS = 4000
HELP = {
    'DEFAULT': {
        'args': '<question|request|instruction>',
        'desc': 'Sends your request to OpenAI\'s ChatGPTv3 and returns the answer.',
    },
}
