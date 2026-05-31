#!/usr/bin/env python3

BINDS = ['@caldera', '@cal']
CHANS = ['debug']
APIURL = {
    'caldera': {
        # Caldera is self-hosted, so the URL is operator-specific.
        # Point this at your Caldera v4+ /api/v2 endpoint. The API key
        # comes from your Caldera config (red/blue accounts each have
        # one; pass whichever role you want the bot to query under).
        # Docs: https://caldera.readthedocs.io/en/latest/_generated/app.html
        'url': 'https://caldera.example.com/api/v2/',
        'key': '<your-caldera-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
# TLS verification — flip to False only when pointing at a self-signed
# internal Caldera. Per-deployment knob; default secure.
VERIFY_TLS = True
MAX_RECORDS = 12
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<subcommand> [id]',
        'desc': (
            'Query a self-hosted MITRE Caldera instance. Subcommands: '
            '`adversaries`, `adversary <id>`, `abilities` (with optional '
            'tactic filter), `ability <id>`, `operations`, `operation <id>`, '
            '`agents`. Configure URL + API key in `settings.py`.'
        ),
    },
}
