#!/usr/bin/env python3
#
# GENERAL INFORMATION
#
# This is an example module that responds to various forms of 'hello'. It describes the basics
# needed to create your own Mattermost channel binds and handlers.
#
# BASIC SETUP
#
# 1) Every module must set a list() of binds to configure what commands to listen for.
# 2) Every module must set a list() of channels to configure what channels to listen in.
# 3) Every module must implement the process(connection, channel, username, params) function.
#    This process() function is called by the main worker thread and returns a dict that tells
#    the main worker thread what to do, such as sending messages to the channel/user.
# 4) Make sure to modify the 'pathlib' construct below to reflect the correct (directory)
#    name for your module: 'commands.<modulename>' and 'commands/<modulename>/settings.py'
#    should be set correctly. This is used for dynamically loading defaults and overwriting
#    them with your own configuration in the 'settings.py' file.
# 5) The module should return a dictionary with a 'messages' key, which contains a list of
#    messages to be sent back to the caller, with a 'text' and optionally an 'uploads' key
#    per message. If populated, the 'uploads' key should contain a list of dictionaries,
#    specifying the 'filename' and 'bytes' keys. Every upload will be attached to that
#    message.
#
#    {'messages': [
#       {'text': 'This is a plain message, without any attachments.', 'uploads': None},
#       {'text': 'This is just a plain message, without any attachments.', },
#       {'text': 'One file is attached to this message.', 'uploads': [{'filename': 'XXX', 'bytes': 'ZZZ'}]},
#       {'text': 'Two files are attached to this message.', 'uploads': [{'filename': 'ABC', 'bytes': 'DEF'}, {'filename': 'GHI', 'bytes': 'JKL'}]},
#       ]
#    }
#
# VARIABLES
#
# 1) BINDS: Python list(): which channel messages to listen to. **MANDATORY**
# 2) CHANS: Python list(): which channel(s) to listen in. **MANDATORY**
# 3) HELP: Python dict(): provides context-sensitive help for your module. The bot will
#    traverse the dictionary and explain all commands. Use the 'DEFAULT' key to let the
#    bot provide a default answer to a generic !help request as well. **OPTIONAL**
#
#       Example: HELP = {
#                           'DEFAULT': {
#                               'args': None,
#                               'desc': 'The bot will reply to your greeting!',
#                           },
#                           '<subcommand>' {
#                               'args': '<value>',
#                               'desc': '<subcommand> does XYZ with <value>',
#                           }
#                       }
#
# Note: If you need custom settings for your module, put them in 'settings.py' so the
#       bot will overload the defaults through its import loader. This should be the
#       file for defining sensitive information such as API tokens, passwords,
#       internal URLs, etc. See the 'pathlib' config parser description/code below.
#
# PROCESS() FUNCTION PARAMETERS/MEANING
#
# 1) Command:    The command that triggered the module (e.g. '@ioc' or '!help')
# 2) Channel:    Channel name were the command was triggered
# 3) Username:   Username that triggered the command
# 4) Params:     Parameters to the command, as a Python list()

from pathlib import Path
try:
    from commands.example import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/example/settings.py').is_file():
        try:
            from commands.example import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    return {'messages': [
        {'text': 'Hello %s!' % (username,)}
    ]}
