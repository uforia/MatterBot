#!/usr/bin/env python3

BINDS = ['@cyberthreat', '@ioc', '@ct']
CHANS = ['debug']
APIURL = {
    'cyberthreat':   {
        'url': 'https://cyberthreat.nl/api/v2/', 
        'apikey': '<APIKEY>',
        'filters': ['type=Bad','type=Bulletproof','type=Fastflux','type=Botnet','credibility=6']
    }
}
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': 'An IP address, hostname, fully qualified domain name, URL etc.\nThe returned actor handle can also be queried for further information.',
        'desc': 'Query the cyberthreat.nl API for the given IoC.',
    },
}


confidence_tabel = {
        1: {'level': 'is', 'short_description':'Confirmed', 'long_description':'Confirmed by other sources: Confirmed by other independent sources; logical in itself; Consistent with other information'},
        2: {'level': 'is probably', 'short_description':'Probable', 'long_description':'Not confirmed but logical in itself and consistent with other information or analysis'},
        3: {'level': 'is possibly', 'short_description':'Possible', 'long_description':'Reasonably logical in itself and agrees with some other information or earlier events'},
        4: {'level': 'might be', 'short_description':'Doubtful', 'long_description':'Not confirmed; possible but not logical; no other information on the subject'},
        5: {'level': 'is probably not', 'short_description':'Improbable', 'long_description':'Improbable: Not confirmed; not logical in itself; contradicted by other information on the subject'},
        6: {'level': 'might or might not', 'short_description':'Truth cannot be judged', 'long_description':'No basis exists for evaluating the validity of the information'},
        7: {'level': 'might be, which is irrelevant,', 'short_description':'Irrelevant', 'long_description':'Irrelevant: Untrue or much less relevant then an other observables'}
    }
