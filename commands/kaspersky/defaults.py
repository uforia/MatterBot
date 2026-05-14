#!/usr/bin/env python3

# NOTE: Kaspersky OpenTIP is intentionally NOT bound to @ioc by default.
# US BIS June-2024 entity-list action + NCSC-NL / multiple EU CSIRT
# advisories against Kaspersky-in-CNI mean integrating Kaspersky into a
# SOC tool is a compliance/audit call the operator should make
# explicitly. To enable Kaspersky on the generic IoC fan-out, add
# '@ioc' to BINDS in settings.py.
BINDS = ['@kaspersky', '@kt']
CHANS = ['debug']
APIURL = {
    'kaspersky': {
        # OpenTIP community endpoint. Free key at
        # https://opentip.kaspersky.com/. Sent via x-api-key header.
        'url': 'https://opentip.kaspersky.com/api/v1/',
        'key': '<your-kaspersky-opentip-api-key-here>',
    },
}
CONTENTTYPE = 'application/json'
MAX_DETECTIONS = 10
MAX_CATEGORIES = 10
MAX_OUTPUT_CHARS = 8000
HELP = {
    'DEFAULT': {
        'args': '<IP|domain|URL|MD5|SHA1|SHA256>',
        'desc': (
            'Kaspersky OpenTIP community reputation lookup. Auto-detects '
            'resource type (IP / domain / URL / file hash) and returns the '
            'verdict zone (Green / Yellow / Red / Grey) plus key metadata. '
            'Requires a free Kaspersky OpenTIP account '
            '(https://opentip.kaspersky.com/).'
        ),
    },
}
