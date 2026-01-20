#!/usr/bin/env python3

import OpenSSL
import re
import ssl

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
