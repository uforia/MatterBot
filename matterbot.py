#!/usr/bin/env python3

import ast
import asyncio
import collections
import concurrent.futures
import copy
import fnmatch
import importlib.util
import json
import logging
import os
import pathlib
import sys
import configargparse
from mattermostdriver import Driver


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
            'basepath'  : options.Matterbot['basepath'],
            'scheme'    : options.Matterbot['scheme'],
            'auth'      : TokenAuth,
            #'debug'     : options.debug,
            'keepalive' : True,
            'keepalive_delay': 30,
            'websocket_kw_args': {'ping_interval': 5},
        })
        try:
            self.mmDriver.login()
        except:
            logging.error("Mattermost server is unreachable. Perhaps it is down, or you might have misconfigured one or more setting(s). Shutting down!")
            return False
        self.me = self.mmDriver.users.get_user(user_id='me')
        self.my_id = self.me['id']
        self.my_team_name = options.Matterbot['teamname']
        self.my_team_id = self.mmDriver.teams.get_team_by_name(self.my_team_name)['id']
        # Load an existing module channel binding map if present
        modulepath = options.Modules['commanddir'].strip('/')
        sys.path.append(modulepath)
        self.commands = {}
        self.binds = []
        self.channelmapping = { 'idtoname': {}, 'nametoid': {}}
        
        try:
            bindmap = pathlib.Path(options.Matterbot['bindmap'])
            if bindmap.is_file():
                with open(options.Matterbot['bindmap']) as f:
                    self.commands = json.load(f)
                    for module in self.commands:
                        self.binds.extend(self.commands[module]['binds'])
            log.info("Loaded existing bindmap file %s: %s" % (options.Matterbot['bindmap'],self.commands))
        except: # There is no existing command map, or it failed loading; create an empty map instead.
            pass
        # Load any new modules
        for root, dirs, files in os.walk(modulepath):
            for module in fnmatch.filter(files, "command.py"):
                module_name = root.split('/')[-1].lower()
                module = importlib.import_module(module_name + '.' + 'command')
                if not module_name in self.commands:
                    module.settings.BINDS = None
                    module.settings.CHANS = None
                    defaults = importlib.import_module(module_name + '.' + 'defaults')
                    if hasattr(defaults, 'BINDS'):
                        module.settings.BINDS = defaults.BINDS
                    if hasattr(defaults, 'CHANS'):
                        module.settings.CHANS = defaults.CHANS
                    if 'settings.py' in files:
                        overridesettings = importlib.import_module(module_name + '.' + 'settings')    
                        if hasattr(overridesettings, 'BINDS'):
                            module.settings.BINDS = overridesettings.BINDS
                        if hasattr(overridesettings, 'CHANS'):
                            module.settings.CHANS = overridesettings.CHANS
                    self.commands[module_name] = {'binds': module.settings.BINDS, 'chans': module.settings.CHANS}
                    self.binds.extend(module.settings.BINDS)
        try:
            with open(options.Matterbot['bindmap'],'w') as f:
                json.dump(self.commands,f)
        except:
            log.error("An error occurred writing the bindmap file: %s" % (options.Matterbot['bindmap'],))
        # Resolve function calls and update the module help
        for root, dirs, files in os.walk(modulepath):
            for module in fnmatch.filter(files, "command.py"):
                module_name = root.split('/')[-1].lower()
                module = importlib.import_module(module_name + '.' + 'command')
                defaults = importlib.import_module(module_name + '.' + 'defaults')
                if hasattr(defaults, 'HELP'):
                    HELP = defaults.HELP
                if 'settings.py' in files:
                    overridesettings = importlib.import_module(module_name + '.' + 'settings')    
                    if hasattr(overridesettings, 'HELP'):
                        HELP = overridesettings.HELP
                self.commands[module_name]['process'] = getattr(module, 'process')
                self.commands[module_name]['help'] = HELP

                
        self.binds = sorted(list(set(self.binds)))
        # Start the websocket
        self.mmDriver.init_websocket(self.handle_raw_message)

    """
    Convert a channel name to an ID if this is done already. Lookups are saved in a two way dict
    self.channelmapping
    """
    def channame_to_chaninfo(self, channame):
        if channame in self.channelmapping['nametoid']:
            return self.channelmapping['nametoid'][channame]
        else:
            try:
                chaninfo = self.mmDriver.channels.get_channel_by_name(self.my_team_id, channame)
            except Exception as e:
                log.error(f"Could not map {channame}: {e}")
                return None
            else:
                self.channelmapping['nametoid'][chaninfo['name']] = chaninfo
                self.channelmapping['idtoname'][chaninfo['id']]   = chaninfo
                return chaninfo
            
    def chanid_to_chaninfo(self, chanid):
        if chanid in self.channelmapping['idtoname']:
            return self.channelmapping['idtoname'][chanid]
        else:
            try:
                chaninfo = self.mmDriver.channels.get_channel(chanid)
            except Exception as e:
                log.error(f"Could not map {chanid}: {e}")
                return None
            else:
                self.channelmapping['nametoid'][chaninfo['name']] = chaninfo
                self.channelmapping['idtoname'][chaninfo['id']]   = chaninfo
                return chaninfo

    async def update_bindmap(self):
        try:
            self.bindmap = copy.deepcopy(self.commands)
            for module in self.bindmap:
                del self.bindmap[module]['help']
                del self.bindmap[module]['process']
            with open(options.Matterbot['bindmap'],'w') as f:
                json.dump(self.bindmap,f)
        except:
            raise
            logging.error("An error occurred updating the `%s` bindmap file; config changes were not successfully saved!" % (options.Matterbot['bindmap'],))

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
            log.error(e)

    async def send_message(self, chanid, text, postid=None):
        try:
            channame = self.chanid_to_channame(chanid)
            log.info('Channel:' + channame + ' <- Message: (' + str(len(text)) + ' chars)')

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
                self.mmDriver.posts.create_post(options={'channel_id': chanid,
                                                         'message': block,
                                                         'root_id': postid,
                                                         })
        except:
            raise


    def channame_to_chanid(self, channame, teamid=None):
        try:
            if not teamid:
                teamid = self.my_team_id
            return self.mmDriver.channels.get_channel_by_name(teamid,channame)['id']
        except:
            return None

    def chanid_to_channame(self, chanid):
        try:
            return self.mmDriver.channels.get_channel(chanid)['name']
        except:
            return None

    def chanid_to_chandisplayname(self, chanid):
        try:
            return self.mmDriver.channels.get_channel(chanid)['display_name']
        except:
            return None

    def channame_to_chandisplayname(self, channame):
        try:
            return self.chanid_to_chandisplayname(self.channame_to_chanid(channame))
        except:
            return None

    def userid_to_username(self,userid):
        try:
            return self.mmDriver.users.get_user(userid)['username']
        except:
            return None


    def isallowed_module(self, user, module, chaninfo):
        """
        Check if we are in a channel or in a private chat
        > There are four types of channels: public channels, private channels, direct messages, and group messages.
        source: https://docs.mattermost.com/collaborate/channel-types.html
        'O' for a public channel, 'P' for a private channel, "D": Direct message channel (1:1), "G": Group message channel (group direct message)
        """
        channame = chaninfo['name']
        if chaninfo['type'] in ('O', 'P'):
            logging.debug(f"Channel name: {chaninfo['name']}")
            if (channame or 'any') in self.commands[module]['chans']:
                return True
        elif chaninfo['type'] in ('D', 'G'):
            """
            Check if a user is in one of the channels that are configured in the modules 'chans'
            """
            memberlist = []
            for channame in self.commands[module]['chans']:
                try:
                    memberlist.extend([_['user_id'] for _ in self.mmDriver.channels.get_channel_members(self.channame_to_chanid(channame))])
                    if user in memberlist:
                        return True
                except:
                    # Apparently the channel does not exist; perhaps it is spelled incorrectly or otherwise a misconfiguration?
                    logging.error("There is a non-existent channel set up in the bot bindings or configuration: %s" % (channame,))
        logging.info(f"User {user} is not allowed to use {module} in {channame}.")
        return False

    async def bind_message(self, userid, post, params, chaninfo, rootid):
        command = post['message'].split()[0]
        chanid = post['channel_id']
        channame = self.chanid_to_channame(chanid)
        username = self.userid_to_username(userid)
        messages = []
        if not params:
            if command in ('!map', '@map'):
                if len(self.commands):
                    chans = set()
                    if (self.my_id and userid) in channame:
                        text =  "**List of modules in direct message:**\n"
                    else:
                        text =  "**List of modules for channel: `%s`**\n" % (self.channame_to_chandisplayname(channame,))
                    text += "\n"
                    text += "\n| **Module Name** | **Available** | **Binds** | **Description** |"
                    text += "\n| :- |  :- | :- |"
                    for module in sorted(self.commands):
                        if self.isallowed_module(userid,module,chaninfo):
                            chans.add(module)
                            text += "\n| %s | **YES** | `%s` | %s |" % (module,'`, `'.join(sorted(self.commands[module]['binds'])),self.commands[module]['help']['DEFAULT']['desc'].replace('|','/'))
                        elif userid in options.Matterbot['botadmins']:
                            chans.add(module)
                            text += "\n| %s | **NO** | `%s` | %s |" % (module,'`, `'.join(sorted(self.commands[module]['binds'])),self.commands[module]['help']['DEFAULT']['desc'].replace('|','/'))
                    text += "\n\n"
                if not len(chans):
                    text = '@' + username + ", I don't know about any commands here.\n"
                text += "*Remember that not every command works everywhere: this depends on the configuration. Modules may offer additional help if you add the subcommand.*"
                messages.append(text)
        else:
            if not userid in options.Matterbot['botadmins']:
                logging.warn("User %s attempted to use a bind command without proper authorization.") % (userid,)
                text = "@" + username + ", you do not have permission to bind commands."
            else:
                all_channel_types = [self.chanid_to_channame(_['id']) for _ in self.mmDriver.channels.get_channels_for_user(self.my_id,self.my_team_id)]
                my_channels = [_ for _ in all_channel_types if not self.my_id in _]
                if not channame in my_channels:
                    text = "@" + username + ", you cannot bind commands to direct message windows."
                else:
                    if params[0] == '*':
                        params = self.commands.keys() # Attempt to enable/disable all modules
                    for modulename in params:
                        if not modulename in self.commands:
                            text = "@" + username + ", there is no `%s` module loaded. Use one of the help commands (`%s`) to see a list of available modules." % (modulename,"`, `".join(options.Matterbot['helpcmds']))
                        elif command in ('!bind', '@bind'):
                            if channame in self.commands[modulename]['chans']:
                                text = "The `%s` module is already available in the `%s` channel." % (modulename,self.channame_to_chandisplayname(channame))
                            else:
                                self.commands[modulename]['chans'].append(channame)
                                text = "The `%s` module is now available in the `%s` channel." % (modulename,self.channame_to_chandisplayname(channame))
                        elif command in ('!unbind', '@unbind'):
                            if not channame in self.commands[modulename]['chans']:
                                text = "The `%s` module is not loaded in the `%s` channel." % (modulename,self.channame_to_chandisplayname(channame))
                            else:
                                self.commands[modulename]['chans'].remove(channame)
                                text = "The `%s` module has been removed from the `%s` channel." % (modulename,self.channame_to_chandisplayname(channame))
                        messages.append(text)
                await self.update_bindmap()
        if len(messages):
            for message in messages:
                await self.send_message(chanid, message, rootid)

    async def help_message(self, userid, params, chaninfo, rootid):
        chanid=chaninfo['id']
        commands = set()
        if not params:
            for module in self.commands:
                if self.isallowed_module(userid, module, chaninfo):
                    for bind in self.commands[module]['binds']:
                        commands.add('`' + bind + '`')
            text =  "I know about: `"+'`, `'.join(sorted(options.Matterbot['helpcmds']))+"`, " + ', '.join(sorted(commands)) + " here.\n"
            text += "*Remember that not every command works everywhere: this depends on the configuration. Modules may offer additional help if you add the subcommand.*"
            await self.send_message(chanid, text, rootid)        
        else:
            # User is asking for specific module help
            for module in self.commands:
                if self.isallowed_module(userid, module, chaninfo):
                    if set(params) & set(self.commands[module]['binds']): # for future use
                        try:
                            text = ''
                            HELP = self.commands[module]['help']
                            paramsubcommands = set(params) & set(HELP)
                            if len(paramsubcommands) == 0:
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
                            else: # paramsubcommands >= 1
                                for subcommand in paramsubcommands:
                                    args = HELP[subcommand]['args'] if HELP[subcommand]['args'] else None
                                    desc = HELP[subcommand]['desc']
                                    text += '**Module**: `' + module + '`/`' + subcommand + '`'
                                    text += '\n**Description**: '
                                    text += desc
                                    if args:
                                        text += '\n**Arguments**: `' + args + '`'
                            if len(text)>0:
                                 await self.send_message(chanid, text, rootid)
                        except NameError:
                            await self.send_message(chanid, text, rootid)

    async def handle_post(self, data: dict):
        if 'sender_name' in data:
            username = data['sender_name']
        else:
            # We're currently not handling users editing messages
            return
        post = json.loads(data['post'])
        userid = post['user_id']
        chanid = post['channel_id']
        chaninfo = self.chanid_to_chaninfo(chanid)
        channame = chaninfo['name']
        rootid = post['root_id'] if len(post['root_id']) else post['id']
        messagelines = post['message'].splitlines()
        # Check if the bot is allowed to respond to its own messages (see config file)
        if options.Matterbot['recursion'] or userid != self.my_id:
            messages = list()
            for mline in messagelines:
                addparams = False
                message = mline.split()
                for idx,word in enumerate(message):
                    if (word in self.binds and not message in options.Matterbot['helpcmds'] and not message in options.Matterbot['mapcmds']) or \
                        word in options.Matterbot['helpcmds'] or \
                        word in options.Matterbot['mapcmds']:
                        messages.append({'command':word,'parameters':[]})
                        addparams = True
                    elif addparams:
                        messages[-1]['parameters'].append(word)
            for messagedict in messages:
                command = messagedict['command']
                params = messagedict['parameters']
                if command in options.Matterbot['helpcmds']:
                    await self.help_message(userid,params,chaninfo,rootid)
                elif command in options.Matterbot['mapcmds']:
                    await self.bind_message(userid,post,params,chaninfo,rootid)
                else:
                    tasks = []
                    for module in self.commands:
                        if command in self.commands[module]['binds']:
                            if self.isallowed_module(userid, module, chaninfo):
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
                                        results.append(executor.submit(self.commands[task]['process'], command, channame, username, params, files, self.mmDriver))
                                    except Exception as e:
                                        text = 'An error occurred within module: '+task+': '+str(type(e))+': '+e
                                        await self.send_message(chanid, text, rootid)
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
                                                        channel_id=chanid,
                                                        files={'files': (filename, payload)}
                                                    )['file_infos'][0]['id']
                                                    file_ids.append(file_id)
                                                self.mmDriver.posts.create_post(options={'channel_id': chanid,
                                                                                        'message': text,
                                                                                        'file_ids': file_ids,
                                                                                        })
                                            else:
                                                await self.send_message(chanid, text, rootid)
                                        else:
                                            await self.send_message(chanid, text, rootid)
                        except Exception as e:
                            text = 'A Python error occurred: '+str(type(e))+': '+str(e)
                            await self.send_message(chanid, text, rootid)

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
        logging.basicConfig(level=0,format='%(levelname)s - %(name)s - %(asctime)s - %(message)s')
    log = logging.getLogger('MatterAPI')
    log.info('Starting MatterBot')
    mm = MattermostManager()
