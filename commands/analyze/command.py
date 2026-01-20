#!/usr/bin/env python3

import hashlib
import traceback

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
    params = ' '.join(params)
    messages = []
    filefields = {
        'name': 'Filename',
        'size': 'Size',
        'mime_type': 'MIME-type',
        'sha256': 'SHA256',
    }
    hashfields = ['sha256']
    try:
        if len(files):
            autoexecs = set()
            header = '**Analysis for `%s` file(s)**\n\n' % (len(files),)
            for filefield in filefields:
                header += '| %s ' % (filefields[filefield],)
            header += '|\n'
            for filefield in filefields:
                if filefields in ('size',):
                    header += '| -: '
                else:
                    header += '| :- '
            header += '|\n'
            message = header
            for file in files:
                id = file['id']
                for filefield in filefields:
                    if filefield in file:
                        message += '| `%s` ' % (file[filefield],)
                    if filefield in hashfields:
                        sha256 = hashlib.sha256(conn.files.get_file(id).content).hexdigest()
                        message += '| `%s` ' % (sha256,)
                        autoexecs.add(sha256)
                message += '|\n'
        message += '\n\n'
        messages.append({'text': message})
        for autoexec in autoexecs:
            for command in settings.AUTOEXEC:
                messages.append({'text': '%s %s' % (command, autoexec)})
    except Exception as e:
        messages.append({'text': 'A Python error occurred searching Tweetfeed: %s\n%s' % (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
