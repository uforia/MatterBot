#!/usr/bin/env python3

import ast
import asyncio
import copy
import fnmatch
import importlib.util
import json
import logging
import os
import pathlib
import sys
import traceback
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
            log.error("Mattermost server is unreachable. Perhaps it is down, or you might have misconfigured one or more setting(s). Shutting down!")
            return False
        self.me = self.mmDriver.users.get_user(user_id='me')
        log.info("Who am I: %s" % (self.me,))
        self.my_id = self.me['id']
        self.my_team_name = options.Matterbot['teamname']
        self.my_team_id = self.mmDriver.teams.get_team_by_name(self.my_team_name)['id']
        # Load an existing module channel binding map if present
        modulepath = options.Modules['commanddir'].strip('/')
        sys.path.append(modulepath)
        self.commands = {}
        self.binds = []
        self.channelmapping = {'idtoname': {}, 'nametoid': {}}
        self.channels = self.mmDriver.channels.get_channels_for_user(self.my_id,self.my_team_id)
        self.feedmap = self.load_feedmap()
        self.bindmap = self.load_bindmap()
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

    def load_bindmap(self):
        try:
            bindmap = pathlib.Path(options.Matterbot['bindmap'])
            if bindmap.is_file():
                with open(options.Matterbot['bindmap']) as f:
                    self.commands = json.load(f)
                    for module in self.commands:
                        self.binds.extend(self.commands[module]['binds'])
                    log.info("Loaded existing bindmap file %s: %s" % (options.Matterbot['bindmap'],self.commands))
        except: # There is no existing command map, or it failed loading; create an empty map instead.
            raise

    def load_feedmap(self):
        try:
            feedmap = pathlib.Path(options.Matterbot['feedmap'])
            if feedmap.is_file():
                with open(options.Matterbot['feedmap']) as f:
                    log.info("Loaded existing feedmap file %s" % (options.Matterbot['feedmap']))
                    return json.load(f)
        except: # There is no existing feed map, or it failed loading; create an empty map instead.
            raise

    async def update_bindmap(self):
        try:
            self.bindmap = copy.deepcopy(self.commands)
            for module in self.bindmap:
                del self.bindmap[module]['help']
                del self.bindmap[module]['process']
            with open(options.Matterbot['bindmap'],'w') as f:
                json.dump(self.bindmap,f)
        except:
            log.error(f"An error occurred updating the `%s` bindmap file; config changes were not successfully saved!" % (options.Matterbot['bindmap'],))

    async def update_feedmap(self):
        try:
            self.newfeedmap = copy.deepcopy(self.feedmap)
            with open(options.Matterbot['feedmap'],'w') as f:
                json.dump(self.newfeedmap,f)
        except:
            log.error(f"An error occurred updating the `%s` feedmap file; config changes were not successfully saved!" % (options.Matterbot['feedmap'],))

    async def handle_raw_message(self, raw_json: str):
        try:
            data = json.loads(raw_json)
            asyncio.create_task(self.handle_message(data))
        except json.JSONDecodeError as e:
            log.error(f"Could not handle raw JSON {raw_json}: {e}")

    async def handle_message(self, message: dict):
        try:
            if 'event' in message:
                post_data = message['data']
                if 'post' in post_data: # We're handling some kind of post, e.g. a channel message
                    await self.handle_post(post_data)
                else: # We're probably handling something administrative, such as channel adds/removals
                    await self.handle_event(post_data)
        except json.JSONDecodeError as e:
            log.error(f"Could not handle message {message}: {e}")

    async def log_message(self, userid, command, params, chaninfo, rootid):
        try:
            logline = None
            channame = chaninfo['name']
            myname = self.userid_to_username(self.my_id)
            if '__' in channame and userid in channame and self.my_id in channame:
                channame = f'Direct Message with me ({myname})'
            username = self.userid_to_username(userid)
            if options.Matterbot['logcmd']:
                logline = f'Channel: {channame} - User: {username} - Command: {command}'
            if options.Matterbot['logcmdparams']:
                if len(params):
                    logline += f' - Params: {params}'
            if logline:
                log.info(f'Command Logging -> {logline}')
        except:
            raise

    async def send_message(self, chanid, text, postid=None):
        try:
            channame = self.chanid_to_chaninfo(chanid)['name']
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
        except Exception as e:
            log.error(f"Could not map {channame} to chanid: {e}")
            return None

    def chanid_to_channame(self, chanid):
        try:
            return self.mmDriver.channels.get_channel(chanid)['name']
        except Exception as e:
            log.error(f"Could not map {chanid} to channame: {e}")
            return None

    def chanid_to_chandisplayname(self, chanid):
        try:
            return self.mmDriver.channels.get_channel(chanid)['display_name']
        except Exception as e:
            log.error(f"Could not map {chanid} to chandisplayname: {e}")
            return None

    def channame_to_chandisplayname(self, channame):
        try:
            return self.chanid_to_chandisplayname(self.channame_to_chanid(channame))
        except Exception as e:
            log.error(f"Could not map {channame} to chandisplayname: {e}")
            return None

    def channame_to_chaninfo(self, channame):
        if channame in self.channelmapping['nametoid']:
            return self.channelmapping['nametoid'][channame]
        else:
            try:
                chaninfo = self.mmDriver.channels.get_channel_by_name(self.my_team_id, channame)
            except Exception as e:
                log.error(f"Could not map {channame} to chaninfo: {e}")
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
                log.error(f"Could not map {chanid} to chaninfo: {e}")
                return None
            else:
                self.channelmapping['nametoid'][chaninfo['name']] = chaninfo
                self.channelmapping['idtoname'][chaninfo['id']]   = chaninfo
                return chaninfo

    def userid_to_username(self, userid):
        try:
            return self.mmDriver.users.get_user(userid)['username']
        except Exception as e:
            log.error(f"Could not map {userid} to username: {e}")
            return None

    def isadmin(self, userid):
        try:
            userinfo = self.mmDriver.users.get_user(userid)
            roles = [_.lower() for _ in userinfo['roles'].split()]
            if any(options.Matterbot['botadmins']) in roles or userid in options.Matterbot['botadmins']:
                return True
        except:
            return None

    def is_in_channel(self, chanid, userid=None):
        if not userid:
            userid = self.my_id if not userid else userid
            self.channels = self.mmDriver.channels.get_channels_for_user(userid,self.my_team_id)
            return True if chanid in [_['id'] for _ in self.channels] else False

    def isallowed_module(self, userid, module, chaninfo):
        """
        Check if we are in a channel or in a private chat
        > There are four types of channels: public channels, private channels, direct messages, and group messages.
        source: https://docs.mattermost.com/collaborate/channel-types.html
        'O' for a public channel, 'P' for a private channel, "D": Direct message channel (1:1), "G": Group message channel (group direct message)
        """
        channame = chaninfo['name']
        username = self.userid_to_username(userid)
        if chaninfo['type'] in ('O', 'P'):
            log.debug(f"Channel name: {chaninfo['name']}")
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
                    if userid in memberlist:
                        return True
                except Exception as e:
                    # Apparently the channel does not exist; perhaps it is spelled incorrectly or otherwise a misconfiguration?
                    log.error("An error occurred during channel parsing: %s" % (str(e),traceback.format_exc()))
        log.info(f"User {userid} is not allowed to use {module} in {channame}.")
        return False

    async def feed_message(self, userid, post, params, chaninfo, rootid):
        self.feedmap = self.load_feedmap()
        command = post['message'].split()[0]
        chanid = post['channel_id']
        channame = chaninfo['name']
        username = self.userid_to_username(userid)
        messages = []
        if not params:
            if command in ('!feeds', '@feeds'):
                if (self.my_id and userid) in channame:
                    text =  "**Feeds do not work in direct messages.**\n"
                    messages.append(text)
                else:
                    enabled_feeds = set()
                    unclassified_feeds = set()
                    if len(self.feedmap):
                        text =  "**List of available topics for channel: `%s`**\n" % (self.channame_to_chandisplayname(channame,))
                        text += "\n"
                        text += "\n| **Topic** | **Available Feed(s)** |"
                        text += "\n| :- | :- |"
                        if 'TOPICS' in self.feedmap:
                            for topic in sorted(self.feedmap['TOPICS']):
                                availablefeeds = self.feedmap['TOPICS'][topic]
                                for module_name in self.feedmap:
                                    if 'NAME' in self.feedmap[module_name]:
                                        if channame in self.feedmap[module_name]['CHANNELS']:
                                            if module_name in availablefeeds:
                                                availablefeeds.remove(module_name)
                                            enabled_feeds.add(module_name)
                                if len(availablefeeds):
                                    availablefeeds_displaynames = set()
                                    for availablefeed in availablefeeds:
                                        displayname = availablefeed
                                        if 'ADMIN_ONLY' in self.feedmap[availablefeed]:
                                            displayname = availablefeed+r'(*)' if self.feedmap[availablefeed]['ADMIN_ONLY'] else availablefeed
                                        availablefeeds_displaynames.add(displayname)
                                    text += f"\n| {topic} | `"+"`, `".join(sorted(availablefeeds_displaynames))+"` |"
                        for module_name in self.feedmap:
                            if 'NAME' in self.feedmap[module_name]:
                                if 'TOPICS' not in self.feedmap[module_name]:
                                    unclassified_feeds.add(module_name)
                                else:
                                    if not len(self.feedmap[module_name]['TOPICS']):
                                        unclassified_feeds.add(module_name)
                        if len(unclassified_feeds):
                            unclassified_feeds_displaynames = set()
                            for unclassified_feed in unclassified_feeds:
                                displayname = unclassified_feed
                                if 'ADMIN_ONLY' in self.feedmap[unclassified_feed]:
                                    displayname = unclassified_feed+r'(*)' if self.feedmap[unclassified_feed]['ADMIN_ONLY'] else unclassified_feed
                                unclassified_feeds_displaynames.add(displayname)
                            text += f"\n| Unclassified | `"+"`, `".join(sorted(unclassified_feeds_displaynames))+"` |"
                        text += "\n\n"
                        text += "*An asterisk after a module name (\*) indicates the feed can only be enabled/disabled by a MatterBot admin.*\n"
                        messages.append(text)
                    if len(enabled_feeds):
                        text = f"Enabled feeds: `"+"` ,`".join(enabled_feeds)+"`"
                        messages.append(text)
                    else:
                        text = "There are no feeds enabled in this channel.\n"
                        messages.append(text)
        else:
            if command in options.Matterbot['feedcmds']:
                if not self.isadmin(userid):
                    if options.Matterbot['feedmode'].lower() == 'admin':
                        logging.warning(f"User {username} ({userid}) attempted to use a feed (un)subscribe command without proper authorization.")
                        text = "@" + username + ", you do not have permission to (un)subscribe from/to feeds."
                        messages.append(text)
                if self.isadmin(userid) or options.Matterbot['feedmode'].lower() == 'user':
                    all_channel_types = [self.chanid_to_channame(_['id']) for _ in self.mmDriver.channels.get_channels_for_user(self.my_id,self.my_team_id) if self.is_in_channel(_['id'])]
                    my_channels = [_ for _ in all_channel_types if not self.my_id in _]
                    if not channame in my_channels:
                        text = f"@{username}, you cannot have feeds in a Direct Message window."
                        messages.append(text)
                    else:
                        feeds_to_consider = set()
                        if params[0] == '*':
                            feeds_to_consider = self.feedmap
                        else:
                            for param in params[0:]:
                                lowercase_topics = {_.lower(): _ for _ in self.feedmap['TOPICS']}
                                if param.lower() in lowercase_topics:
                                    topic_key = lowercase_topics[param]
                                    for module_name in self.feedmap['TOPICS'][topic_key]:
                                        feeds_to_consider.add(module_name)
                                else:
                                    feeds_to_consider.add(param)
                        switched_feeds = set()
                        blocked_feedchanges = set()
                        if len(params):
                            if command in ('!unsub', '!unsubscribe', '@unsub', '@unsubscribe'):
                                mode = 'disable'
                            elif command in ('!sub', '!subscribe', '@sub', '@subscribe'):
                                mode = 'enable'
                            for module_name in feeds_to_consider:
                                if module_name in self.feedmap:
                                    ADMIN_ONLY = self.feedmap[module_name]['ADMIN_ONLY'] if 'ADMIN_ONLY' in self.feedmap[module_name] else True
                                    if not ADMIN_ONLY or self.isadmin(userid):
                                        if mode == 'enable':
                                            if 'NAME' in self.feedmap[module_name]:
                                                if not channame in self.feedmap[module_name]['CHANNELS']:
                                                    self.feedmap[module_name]['CHANNELS'].append(channame)
                                                    switched_feeds.add(module_name)
                                        elif mode == 'disable':
                                            if 'NAME' in self.feedmap[module_name]:
                                                if channame in self.feedmap[module_name]['CHANNELS']:
                                                    self.feedmap[module_name]['CHANNELS'].remove(channame)
                                                    switched_feeds.add(module_name)
                                    else:
                                        blocked_feedchanges.add(module_name)
                                if len(blocked_feedchanges):
                                    logging.warning(f"User {username} ({userid}) attempted an (un)subscribe from/to `"+"`, `".join(blocked_feedchanges)+f"` in `{channame}` without authorization.")
                                    text = f"@{username}, you do not have permission to (un)subscribe from/to `"+"`, `".join(blocked_feedchanges)+f"` in `{channame}`."
                                    messages.append(text)
                                if len(switched_feeds):
                                    logging.info(f"User {username} ({userid}) (un)subscribed from/to in `{channame}`: `"+"`, `".join(switched_feeds)+"`.")
                                    text = f"@{username}, the following feeds were {mode}d in `{channame}`: `"+"`, `".join(switched_feeds)+"`."
                                    messages.append(text)
                            await self.update_feedmap()
                elif not self.isadmin(userid) and options.Matterbot['feedmode'].lower() == 'admin':
                    text = f"@{username}, feed (un)subscription is restricted to administrators in the current bot configuration."
                    messages.append(text)
                else:
                    text = f"@{username}, how did you end up here?"
                    messages.append(text)
        if len(messages):
            for message in messages:
                await self.send_message(chanid, message, rootid)

    async def bind_message(self, userid, post, params, chaninfo, rootid):
        command = post['message'].split()[0]
        chanid = post['channel_id']
        channame = chaninfo['name']
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
                    text += "\n| :- | :- | :- | :- |"
                    for module in sorted(self.commands):
                        if self.isallowed_module(userid,module,chaninfo):
                            chans.add(module)
                            if 'binds' in self.commands[module] and 'help' in self.commands[module]:
                                text += "\n| %s | **YES** | `%s` | %s |" % (module,'`, `'.join(sorted(self.commands[module]['binds'])),self.commands[module]['help']['DEFAULT']['desc'].replace('|','/'))
                        elif self.isadmin(userid):
                            chans.add(module)
                            if 'binds' in self.commands[module] and 'help' in self.commands[module]:
                                text += "\n| %s | **NO** | `%s` | %s |" % (module,'`, `'.join(sorted(self.commands[module]['binds'])),self.commands[module]['help']['DEFAULT']['desc'].replace('|','/'))
                    text += "\n\n"
                if not len(chans):
                    text = '@' + username + ", I don't know about any commands here.\n"
                text += "*Remember that not every command works everywhere: this depends on the configuration. Modules may offer additional help if you add the subcommand.*"
                messages.append(text)
        else:
            if not self.isadmin(userid):
                logging.warning(f"User {username} ({userid}) attempted to use a bind command without proper authorization.")
                text = "@" + username + ", you do not have permission to bind commands."
            else:
                all_channel_types = [self.chanid_to_channame(_['id']) for _ in self.mmDriver.channels.get_channels_for_user(self.my_id,self.my_team_id) if self.is_in_channel(_['id'])]
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
        chanid = chaninfo['id']
        commands = set()
        if not params:
            for module in self.commands:
                if self.isallowed_module(userid, module, chaninfo):
                    for bind in self.commands[module]['binds']:
                        commands.add('`' + bind + '`')
            text =  "I know about: `"+'`, `'.join(sorted(options.Matterbot['helpcmds']))+"`, " + ', '.join(sorted(commands)) + " here.\n"
            text += "Every command has its own specific help. For example: `!help @dice` will show you how to use the `@dice` command.\n"
            text += "*Remember: not every command works in every channel: this depends on a module's configuration*"
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

    async def handle_event(self, event: dict):
        eventtype = event['type'] if 'type' in event else None
        chanid = event['channel_id'] if 'channel_id' in event else None
        if chanid:
            channame = self.channelmapping['idtoname'][chanid]['name'] if chanid in self.channelmapping['idtoname'] else None
        userid = event['user_id'] if 'user_id' in event else None
        if userid:
            username = self.userid_to_username(userid)
        if not eventtype: # Not a regular type of event, check for the various types
            if 'remover_id' in event and [chanid not in self.mmDriver.channels.get_channels_for_user(self.my_id,self.my_team_id)]: # Removed from a channel!
                userid = event['remover_id']
                username = self.userid_to_username(userid)
                for modulename in self.commands:
                    if channame in self.commands[modulename]['chans']:
                        self.commands[modulename]['chans'].remove(channame)
                        log.info(f"I was just removed from the '{channame}' ({chanid}) channel by '{username}' ({userid}). Existing module bindings for the channel were removed the config file.")
                await self.update_bindmap()


    async def call_module(self, module, command, channame, rootid, username, params, files, conn):
        try:
            chanid = self.channame_to_chanid(channame)
            async with asyncio.timeout(30):
                result = self.commands[module]['process'](command, channame, username, params, files, conn)
            # Command logging: see config.defaults.yaml for clarification
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
                                file_id = conn.files.upload_file(
                                    channel_id=chanid,
                                    files={'files': (filename, payload)}
                                )['file_infos'][0]['id']
                                file_ids.append(file_id)
                            conn.posts.create_post(options={'channel_id': chanid,
                                                                    'message': text,
                                                                    'root_id': rootid,
                                                                    'file_ids': file_ids,
                                                                    })
                        else:
                            await self.send_message(chanid, text, rootid)
                    else:
                        await self.send_message(chanid, text, rootid)
        except Exception as e:
            text = "An error occurred during the %s module call: %s" % (str(module),traceback.format_exc())
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
        # We're probably handling a regular message; make sure to check we're allowed to respond our own messages too (see config file)
        # Additionally, check if we're not self-triggering on the display of the bind map
        if options.Matterbot['recursion'] or userid != self.my_id:
            messages = list()
            for mline in messagelines:
                addparams = False
                message = mline.split()
                for idx,word in enumerate(message):
                    if ((word in self.binds) \
                        and (message[idx-1] not in options.Matterbot['helpcmds'] and message[idx-1] not in options.Matterbot['mapcmds'] \
                        and message[idx-1] not in options.Matterbot['feedcmds'] ) \
                        or (word in options.Matterbot['helpcmds']) \
                        or ((word in options.Matterbot['mapcmds']) and (message[idx-1] not in options.Matterbot['helpcmds'] )) \
                        or ((word in options.Matterbot['feedcmds']) and (message[idx-1] not in options.Matterbot['helpcmds'] ))  ):
                        messages.append({'command':word,'parameters':[]})
                        addparams = True
                    elif addparams:
                        messages[-1]['parameters'].append(word)
            log.debug(f"Messages: {messages}")
            for messagedict in messages:
                command = messagedict['command']
                params = messagedict['parameters']
                if command in options.Matterbot['helpcmds']:
                    await self.log_message(userid, command, params, chaninfo, rootid)
                    await self.help_message(userid, params, chaninfo, rootid)
                elif command in options.Matterbot['mapcmds']:
                    await self.log_message(userid, command, params, chaninfo, rootid)
                    await self.bind_message(userid, post, params, chaninfo, rootid)
                elif command in options.Matterbot['feedcmds']:
                    await self.log_message(userid, command, params, chaninfo, rootid)
                    await self.feed_message(userid, post, params, chaninfo, rootid)
                else:
                    await self.log_message(userid, command, params, chaninfo, rootid)
                    tasks = []
                    if not any(_ in post['message'] for _ in ('| **YES** |', '| **NO** |', 'I know about `!help')):
                        for module in self.commands:
                            if command in self.commands[module]['binds']:
                                if self.isallowed_module(userid, module, chaninfo):
                                    if not module in tasks:
                                        files = []
                                        if 'metadata' in post:
                                            if 'files' in post['metadata']:
                                                if len(post['metadata']['files']):
                                                    files = post['metadata']['files']
                                        try:
                                            async with asyncio.timeout(30):
                                                await self.call_module(module, command, channame, rootid, username, params, files, self.mmDriver)
                                        except asyncio.TimeoutError:
                                            text = f"Error: the command to the {module} module timed out while processing/waiting for a response."
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
        logging.basicConfig(level=logging.INFO, filename=options.Matterbot['logfile'], format='%(levelname)s - %(name)s - %(asctime)s - %(message)s')
    else:
        logging.basicConfig(level=logging.DEBUG,format='%(levelname)s - %(name)s - %(asctime)s - %(message)s')
    log = logging.getLogger('MatterBot')
    log.info('Starting MatterBot')
    mm = MattermostManager()