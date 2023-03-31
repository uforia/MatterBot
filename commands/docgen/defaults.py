#!/usr/bin/env python3

BINDS = ['@docgen']
CHANS = ['debug']
CONTENTTYPE = 'application/json'
APIURL = {
    'docgen':   {
        'url': '<your WikiJS instance\'s URL here>',
        'key': '<your WikiJS\' API token here>',
    },
}
HELP = {
    'DEFAULT': {
        'args': 'RRP, DFIR or CAR',
        'desc': 'Generate a skeleton Retainer Response Plan, Digital Forensics / Incident Response or Compromise Assessment document in MD format.',
    },
    'RRP': {
        'args': '<customer ID>,<Process ID #1>,<Process ID #2>,...,<Process ID #3>',
        'desc': 'Generate an Retainer Response Plan skeleton document, based on the given process IDs and tailored to the given customer ID.',
    },
    'DFIR': {
        'args': '<customer ID>,<Process ID #1>,<Process ID #2>,...,<Process ID #3>',
        'desc': 'Generate a Digital Forensics and Incident Response skeleton document, based on the given process IDs and tailored to the given customer ID.',
    },
    'CAR': {
        'args': '<customer ID>,<Process ID #1>,<Process ID #2>,...,<Process ID #3>',
        'desc': 'Generate a Compromise Assessment skeleton document, based on the given process IDs and tailored to the given customer ID.',
    },
}
