#!/usr/bin/env python3

import OpenSSL
import re
import ssl

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
            messages = []
            for param in params:
                CNs = []
                param = param.replace('[.]','.')
                if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-9]*)?$", param):
                    ipaddress = param.split(':')[0]
                    port = int(param.split(':')[1]) if ':' in param else 443
                    message = '**TLSGrab** Canonical names for `'+ipaddress+'`:`'+str(port)+'`: '
                    try:
                        cert = ssl.get_server_certificate((ipaddress, port))
                        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
                        for component in x509.get_subject().get_components():
                            if component[0] == b'CN':
                                CNs.append(component[1].decode('utf-8').replace('.','[.]'))
                        if len(CNs)>0:
                            message += '`'+'`, `'.join(CNs)+'`'
                    except:
                        message += 'could not be retrieved.'
                    messages.append({'text': message})
            return {'messages': messages}
        except Exception as e:
            return {'messages': [
                {'text': 'An error occurred in TLSGrab: `%s`' % str(e)},
            ]}
