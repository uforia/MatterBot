#!/usr/bin/env python3

import random
import re
from pathlib import Path
try:
    from commands.diceroll import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/diceroll/settings.py').is_file():
        try:
            from commands.diceroll import settings
        except ModuleNotFoundError: # local test run
            import settings

async def process(command, channel, username, params):
    if len(params)>0:
        try:
            params = params[0]
            if re.search(r"^[0-9]{0,3}d[0-9]{0,3}$", params):
                total = 0
                numdice, dicevalue = params.split('d')
                for _ in range(int(numdice)):
                    total += random.randint(1, int(dicevalue))
                return {'messages': [
                    {'text': 'You rolled `' + params + '` and got: `' + str(total) + '`'}
                ]}
            else:
                return {'messages': [
                    {'text': 'I can\'t roll `%s`, `%s`!' % (params, username)}
                ]}
        except Exception as e:
            return {'messages': [
                {'text': 'An error occurred with rolling `%s`:\nError: `%s`' % (params, e)},
            ]}
