#!/usr/bin/env python3

import random
import re

### Dynamic configuration loader (do not change/edit)
import importlib
from pathlib import Path
_pkg_name = Path(__file__).parent.name
try:
    defaults_mod = importlib.import_module(f'commands.{_pkg_name}.defaults')
except ModuleNotFoundError:
    try:
        defaults_mod = importlib.import_module('defaults')
    except ModuleNotFoundError:
        print(f"Module {_pkg_name} could not be loaded due to a missing default configuration.")
try:
    settings_mod = importlib.import_module(f'commands.{_pkg_name}.settings')
except ModuleNotFoundError:
    try:
        settings_mod = importlib.import_module('settings')
    except ModuleNotFoundError:
        settings_mod = None
settings = {k: v for k, v in vars(defaults_mod).items() if not k.startswith('__')}
if settings_mod:
    settings.update({k: v for k, v in vars(settings_mod).items() if not k.startswith('__')})
from types import SimpleNamespace
settings = SimpleNamespace(**settings)
### Loader end, actual module functionality starts here

def process(command, channel, username, params, files, conn):
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
