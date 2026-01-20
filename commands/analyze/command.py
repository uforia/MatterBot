#!/usr/bin/env python3

import hashlib
import traceback

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
