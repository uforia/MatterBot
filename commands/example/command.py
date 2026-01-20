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
# 5) Files:      Attachments that were passed to the bot with the command
# 6) Conn:       The raw connection object to Mattermost. Check the mattermostdriver
#                documentation for more information. **WARNING**: It is dangerous to
#                directly communicate with the Mattermost server if you do not know
#                what you are doing, and you may experience unexpected crashes or
#                behaviour. Use this at your own risk!

import re

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
    # Common regex that can be used to filter out or replace
    # characters that cause MarkDown formatting issues.
    stripchars = r'\[\]\n\r\'\"|'
    regex = re.compile('[%s]' % stripchars)

    # List of messages that this module replies with.
    # Normal text messages are:
    # {'text': '<message>'}
        # Optionally the list item may also have an 'uploads' key:
    # {'text': '<message'>, 'uploads': [ ... ]}
    # The 'uploads' values are dictionary entries containing
    # a 'filename' and 'bytes' keys:
    # 'uploads': [{'filename': '<filename'>, 'bytes': bytes}]
    # Every dictionary item gets added as a file upload to the
    # text message attachments.
    messages = []

    # It is highly recommended to use a custom User-Agent to
    # prevent certain APIs / WAFs from blocking you based on the
    # Python requests default header.
    headers = {
        'Content-Type': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for Example Module v1.0',
    }

    # Let's deal with the command now...
    try:
        # In this example, we just say hi back to the user!
        messages.append({'text': f"It is nice to meet you, {username,}!"})
    except:
        pass
    finally:
        # Yes, this is an unusual and non-compliant code block, but it is there
        # to ensure that the bot responds to a command and is able to return
        # errors coming from its submodules using the same 'API'.
        return {'messages': messages}