#!/usr/bin/env python3

import hashlib
import traceback
from pathlib import Path
try:
    from commands.analyze import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/analyze/settings.py').is_file():
        try:
            from commands.analyze import settings
        except ModuleNotFoundError: # local test run
            import settings

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
