#!/usr/bin/env python3

BINDS = ['@malapi', '@ma']
CHANS = ['debug']
APIURL = {
    'malapi': {
        # MalAPI.io maps Windows APIs to malware tradecraft / MITRE
        # techniques. URL_PATTERN is interpolated with `{api}` (case-
        # preserved) so the operator can retarget if the site path
        # changes. No auth required.
        'url_pattern': 'https://malapi.io/winapi/{api}',
        'key': '',
    },
}
CONTENTTYPE = 'application/json'
MAX_TECHNIQUES = 12
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<Windows API name>',
        'desc': (
            'Look up a Windows API on malapi.io. Returns the owning library, '
            'a short description, MSDN link, and the malware tradecraft / '
            'MITRE ATT&CK techniques the API is associated with. No auth '
            'required.'
        ),
    },
}
