#!/usr/bin/env python3

CHANS = ['debug']
BINDS = ['@rl', '@ransomlook']
APIURL = {
    'ransomlook':   {
        'url': 'https://www.ransomlook.io/api/',
    },
}
WIDTH = 6 # Number of columns in grouped displays
LIMIT = 10
CONTENTTYPE = 'application/json'
HELP = {
    'DEFAULT': {
        'args': '<group|groups|market|markets|posts|tgchannels|tgmessages>',
        'desc': 'Query Ransomlook for information. For subcommand usage, see the specific subcommand '
                'help information.',
    },
    'group': {
        'args': '<group name> [#]',
        'desc': 'Show the last # (number) of posts by <group name>, e.g.: `@ransomlook group '
                'Conti 20`. [#] is optional and defaults to 10.',
    },
    'groups': {
        'args': None,
        'desc': 'List all groups that are being tracked.',
    },
    'market': {
        'args': '<market name> [#]',
        'desc': 'Show the last # (number) of scrapes in <market name>, e.g.: `@ransomlook market '
                'kraken 3`. [#] is optional and defaults to 10.',
    },
    'markets': {
        'args': None,
        'desc': 'List all markets that are being tracked.',
    },
    'posts': {
        'args': '[string] [#]',
        'desc': 'If [string] (optional) is specified, only show recent posts (default: `%s` posts) ' % (LIMIT,) +
                'that contain [string].',
    },
    'tgchannels': {
        'args': None,
        'desc': 'List all available Telegram channels that are being tracked.',
    },
    'tgmessages': {
        'args': '<channel name> [string]',
        'desc': 'Search the Telegram channel <channel name> for messages containing [string] (optional). '
                'If [string] is omitted, show the last 10 posts in that channel.'
    },
}
