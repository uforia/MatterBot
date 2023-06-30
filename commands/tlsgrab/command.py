#!/usr/bin/env python3

import OpenSSL
import re
import ssl
from pathlib import Path
try:
    from commands.tlsgrab import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/tlsgrab/settings.py').is_file():
        try:
            from commands.tlsgrab import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params):
    if len(params)>0:
        try:
            messages = []
            for param in params:
                CNs = []
                param = param.replace('[.]','.')
                if re.search(r"^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])(\:[0-9]*)?$", param):
                    ipaddress = param.split(':')[0]
                    port = int(param.split(':')[1]) if ':' in param else 443
                try:
                    message = '**TLSGrab** Canonical names for `'+ipaddress+'`:`'+str(port)+'`: '
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
