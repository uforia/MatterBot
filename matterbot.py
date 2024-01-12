#!/usr/bin/env python3

import ast
import asyncio
import concurrent.futures
import fnmatch
import importlib.util
import json
import logging
import os
import sys
import tempfile
import configargparse
from mattermostdriver import Driver
from pathlib import Path


class TokenAuth():
    def __call__(self, r):
        r.headers['Authorization'] = "Bearer %s" % options.Matterbot['password']
        r.headers['X-Requested-With'] = 'XMLHttpRequest'
        return r

class MattermostManager(object):
    def __init__(self):
        self.mmDriver = Driver(options={
            'url'       : options.Matterbot['host'],
            'port'      : options.Matterbot['port'],
            'login_id'  : options.Matterbot['username'],
            'token'     : options.Matterbot['password'],
            'auth'      : TokenAuth,
            #'debug'     : options.debug,
            'basepath'  : '/api/v4',
            'keepalive' : True,
            'keepalive_delay': 30,
            'scheme'    : options.Matterbot['scheme'],
            'websocket_kw_args': {'ping_interval': 5},
        })
        self.mmDriver.login()
        self.me = self.mmDriver.users.get_user( user_id='me' )
        self.my_team_id = self.mmDriver.teams.get_team_by_name(options.Matterbot['teamname'])['id']

        # Map all the commands to their modules
        self.commands = {}
        modulepath = options.Modules['commanddir'].strip('/')
        sys.path.append(modulepath)
        for root, dirs, files in os.walk(modulepath):
            for module in fnmatch.filter(files, "command.py"):
                if 'defaults.py' in files:
                    module_name = root.split('/')[-1].lower()
                    module = importlib.import_module(module_name + '.' + 'command')
                    defaults = importlib.import_module(module_name + '.' + 'defaults')
                    if hasattr(defaults, 'HELP'):
                        HELP = defaults.HELP
                    else:
                        HELP = 'No help available'
                    if 'settings.py' in files:
                        overridesettings = importlib.import_module(module_name + '.' + 'settings')    
                        if hasattr(overridesettings, 'HELP'):
                            HELP = overridesettings.HELP
                    self.commands[module_name] = {'binds': module.settings.BINDS, 'chans': module.settings.CHANS, 'help': HELP, 'process': getattr(module, 'process')}
        # Start the websocket
        self.mmDriver.init_websocket(self.handle_raw_message)

    async def handle_raw_message(self, raw_json: str):
        try:
            data = json.loads(raw_json)
            asyncio.create_task(self.handle_message(data))
        except json.JSONDecodeError as e:
            return

    async def handle_message(self, message: dict):
        try:
            if 'event' in message:
                post_data = message['data']
                if 'post' in post_data:
                    await self.handle_post(post_data)
        except json.JSONDecodeError as e:
            print(('ERROR'), e)

    async def send_message(self, channel, text, postid=None):
        try:
            channelname = channel.lower()
            log.info('Channel:' + channelname + ' <- Message: (' + str(len(text)) + ' chars)')
            if len(text) > options.Matterbot['msglength']: # Mattermost message limit
                blocks = []
                lines = text.split('\n')
                blocksize = 0
                block = ''
                for line in lines:
                    lensize = len(line)
                    if (blocksize + lensize) < options.Matterbot['msglength']:
                        blocksize += lensize
                        block += line + '\n'
                    else:
                        blocks.append(block.strip())
                        blocksize = 0
                        block = ''
                blocks.append(block.strip())
            else:
                blocks = [text]
            for block in blocks:
                self.mmDriver.posts.create_post(options={'channel_id': channel,
                                                         'message': block,
                                                         'root_id': postid
                                                         })
        except:
            raise

    async def handle_post(self, data: dict):
        my_id = self.me['id']
        if 'sender_name' in data:
            username = data['sender_name']
        else:
            # We're currently not handling users editing messages
            return
        post = json.loads(data['post'])
        userid = post['user_id']
        postid = post['id']
        channelinfo = self.mmDriver.channels.get_channel(post['channel_id'])
        userchannels = [i['name'] for i in self.mmDriver.channels.get_channels_for_user(userid, self.my_team_id)]
        channelname = channelinfo['name']
        channelid = channelinfo['id']
        message = post['message'].split(' ')
        commands = set()
        if True:
        #if userid != my_id: <-- start working on self-calling bot mechanisms
            command = message[0].lower().strip()
            try:
                params = message[1:]
            except IndexError:
                params = None
            # Generic !help function
            if command == '!help' and not params:
                for module in self.commands:
                    for chan in self.commands[module]['chans']:
                        for bind in self.commands[module]['binds']:
                            if channelname == chan or (((my_id and userid) in channelname) and chan in userchannels):
                                commands.add('`' + bind + '`')
                text = username + " I know about: `!help`, " + ', '.join(sorted(commands)) + " here. Remember that not every command works everywhere: this depends on the configuration. Modules may offer additional help via `!help <command>`."
                await self.send_message(channelid, text)
            else:
                # User is asking for specific module help
                for module in self.commands:
                    if channelname in self.commands[module]['chans'] or (((my_id and userid) in channelname) and channelname in userchannels or self.commands[module]['chans'] == 'any'):
                        if command == '!help' and params and params[0] in self.commands[module]['binds']:
                            try:
                                text = ''
                                HELP = self.commands[module]['help']
                                if len(params)==1:
                                    if 'DEFAULT' in HELP:
                                        # Trigger the default help message
                                        args = HELP['DEFAULT']['args'] if HELP['DEFAULT']['args'] else None
                                        desc = HELP['DEFAULT']['desc']
                                        text += '**Module**: `' + module + '`'
                                        text += '\n**Description**: '
                                        text += desc
                                        if args:
                                            text += '\n**Arguments**: `' + args + '`'
                                        subcommands = set()
                                        if len(HELP)>1:
                                            text += '\n**Subcommmands**: '
                                        for subcommand in HELP:
                                            if subcommand != 'DEFAULT':
                                                subcommands.add(subcommand)
                                        if len(subcommands)>0:
                                            text += '`' + '`, `'.join(subcommands) + '`'
                                else:
                                    subcommand = params[1]
                                    if subcommand in HELP:
                                        args = HELP[subcommand]['args'] if HELP[subcommand]['args'] else None
                                        desc = HELP[subcommand]['desc']
                                        text += '**Module**: `' + module + '`/`' + subcommand + '`'
                                        text += '\n**Description**: '
                                        text += desc
                                        if args:
                                            text += '\n**Arguments**: `' + args + '`'
                                if len(text)>0:
                                    await self.send_message(channelid, text, postid)
                            except NameError:
                                await self.send_message(channelid, 'No additional help available for the `' + module + '` module.')
            # Normal command
            if command != '!help':
                tasks = []
                for module in self.commands:
                    if command in self.commands[module]['binds']:
                        if channelname in self.commands[module]['chans'] or (((my_id and userid) in channelname) and channelname in userchannels):
                            if not module in tasks:
                                tasks.append(module)
                if len(tasks):
                    try:
                        results = []
                        files = []
                        if 'metadata' in post:
                            if 'files' in post['metadata']:
                                if len(post['metadata']['files']):
                                    files = post['metadata']['files']
                        with concurrent.futures.ThreadPoolExecutor(max_workers=None) as executor:
                            for task in tasks:
                                try:
                                    results.append(executor.submit(self.commands[task]['process'], command, channelname, username, params, files, self.mmDriver))
                                except Exception as e:
                                    text = 'An error occurred within module: '+task+': '+str(type(e))+': '+e
                                    await self.send_message(channelid, text, postid)
                        for _ in concurrent.futures.as_completed(results):
                            result = _.result()
                            
                            if result and 'messages' in result:
                                for message in result['messages']:
                                    if 'text' in message:
                                        text = message['text']
                                    if 'uploads' in message:
                                        if message['uploads'] != None:
                                            file_ids = []
                                            for upload in message['uploads']:
                                                filename = upload['filename']
                                                payload = upload['bytes']
                                                if not isinstance(payload, (bytes, bytearray)):
                                                    payload = payload.encode()
                                                file_id = self.mmDriver.files.upload_file(
                                                    channel_id=channelid,
                                                    files={'files': (filename, payload)}
                                                )['file_infos'][0]['id']
                                                file_ids.append(file_id)
                                            self.mmDriver.posts.create_post(options={'channel_id': channelid,
                                                                                     'message': text,
                                                                                     'file_ids': file_ids,
                                                                                     })
                                        else:
                                            await self.send_message(channelid, text, postid)
                                    else:
                                        await self.send_message(channelid, text, postid)
                    except Exception as e:
                        text = 'A Python error occurred: '+str(type(e))+': '+str(e)
                        await self.send_message(channelid, text)
                        raise



if __name__ == '__main__' :
    '''
    Interactive run from the command-line
    '''
    parser = configargparse.ArgParser(config_file_parser_class=configargparse.YAMLConfigFileParser,
                                      description='Matterbot loads modules '
                                                  'and sends their output '
                                                  'to Mattermost.',
                                                  default_config_files=['config.yaml'])
    parser.add('--Matterbot', type=str, help='MatterBot configuration, as a dictionary (see YAML config)')
    parser.add('--Modules', type=str, help='Modules configuration, as a dictionary (see YAML config)')
    parser.add('--debug', default=False, action='store_true', help='Enable debug mode and log to foreground')
    options, unknown = parser.parse_known_args()
    options.Matterbot = ast.literal_eval(options.Matterbot)
    options.Modules = ast.literal_eval(options.Modules)
    if not options.debug:
        logging.basicConfig(filename=options.Matterbot['logfile'], format='%(levelname)s - %(name)s - %(asctime)s - %(message)s')
    else:
        logging.basicConfig(format='%(levelname)s - %(name)s - %(asctime)s - %(message)s')
    log = logging.getLogger( 'MatterAPI' )
    log.info('Starting MatterBot')
    mm = MattermostManager()
