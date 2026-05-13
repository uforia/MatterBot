#!/usr/bin/env python3

# Bindings that trigger this command in any channel. The bot owner can override
# in settings.py per the usual module convention.
BINDS = ['@welcome']

# Use the 'any' wildcard so admins can configure welcome in any channel the
# bot is in. The ACL fix in PR #165 (matterbot.py:isallowed_module) makes
# 'any' a real wildcard token. Operators who haven't merged that fix yet can
# replace this with an explicit channel list in settings.py.
CHANS = ['any']

CONTENTTYPE = 'application/json'

# Path to the SQLite state file. Lives next to this module so all welcome
# state is co-located with the code that uses it. Override in settings.py
# if a different location is preferred.
import os as _os
DB_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'state.db')

# Default delivery mode for a freshly-configured channel. Operators can
# change per-channel via `@welcome delivery <mode>`. See HELP for modes.
DEFAULT_DELIVERY = 'dm'

# Maximum allowed length of a welcome message body. Mattermost enforces its
# own ceiling (config.defaults.yaml Matterbot.msglength = 16383), but a
# tighter cap here is friendlier — multi-screen walls of text get truncated
# at submit-time rather than at delivery.
MAX_MESSAGE_LEN = 8192

HELP = {
    'DEFAULT': {
        'args': '<subcommand> [args]',
        'desc': 'Per-channel welcome messages. Subcommands: '
                '`set <message>`, `get`, `clear`, '
                '`delivery <dm|channel|both>`, `greet <text>`, `test`, `list`, '
                '`reset [@user]`, '
                '`admin add @user`, `admin remove @user`, `admin list`. '
                'Authorization: system_admin OR channel_admin (Mattermost role on the target channel) '
                'OR per-channel allowlist. `{user}` in the message expands to the joining user\'s mention.',
    },
}
