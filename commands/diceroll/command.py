#!/usr/bin/env python3

import random
import re

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
_pkg = __package__ or Path(__file__).parent.name
def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None
_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
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
