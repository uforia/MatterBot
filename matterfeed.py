#!/usr/bin/env python3

import ast
from concurrent.futures import TimeoutError, CancelledError
import configargparse
import fnmatch
import importlib.util
import json
import logging
import pebble
import os
import shelve
import sys
import time
import traceback
import uuid
from mattermostdriver import Driver


class TokenAuth():
    def __call__(self, r):
        r.headers['Authorization'] = "Bearer %s" % options.Matterbot['password']
        r.headers['X-Requested-With'] = 'XMLHttpRequest'
        return r


class MattermostManager(object):
    def __init__(self, log):
        self.log = log
        if options.debug:
            self.log.info("Going to set up driver for connection to %s " % (options.Matterbot['host'],))
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
        self.me = self.mmDriver.users.get_user( user_id='me' )
        self.my_team_id = self.mmDriver.teams.get_team_by_name(options.Matterbot['teamname'])['id']
        self.channels = {}
        self.test = {}
        self.feedmap = self.update_feedmap()
        userchannels = self.mmDriver.channels.get_channels_for_user(self.me['id'],self.my_team_id)
        for userchannel in userchannels:
            channel_info = self.mmDriver.channels.get_channel(userchannel['id'])
            self.channels[channel_info['name']] = channel_info['id']

    def update_feedmap(self):
        try:
            with open(options.Modules['feedmap'],'r') as f:
                return json.load(f)
        except:
            log.error(f"Error   : Cannot read {options.Modules['feedmap']} file. Announcements in additional channels might not work!")
            return {}

    def createPost(self, channel, text, uploads = []):
        try:
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
                if len(uploads):
                    file_ids = []
                    for upload in uploads['uploads']:
                        filename = upload['filename']
                        payload = upload['bytes']
                        if not isinstance(payload, (bytes, bytearray)):
                            payload = payload.encode()
                        file_id = self.mmDriver.files.upload_file(
                            channel_id=channel,
                            files={'files': (filename, payload)}
                        )['file_infos'][0]['id']
                        file_ids.append(file_id)
                    self.mmDriver.posts.create_post(options={'channel_id': channel,
                                                            'message': block,
                                                            'file_ids': file_ids,
                                                            })
                else:
                    self.mmDriver.posts.create_post(options={'channel_id': channel,
                                                            'message': block,
                                                            })
        except Exception as e:
            if options.debug:
                self.log.error(f"Error   : Cannot post channel message: {str(e)}\nTraceback: {traceback.format_exc()}")

    def handleMsg(self, channel, module_name, content, uploads = None):
        if options.debug:
            self.log.info(f"Message  : {module_name.lower()} => {channel} => {content.replace('\n','. ')[:40]} ...")
        if uploads:
            try:
                self.createPost(self.channels[channel], content, uploads)
            except Exception as e:
                self.log.error(f"Error   : Cannot handle {module_name} message: {str(e)}\nTraceback: {traceback.format_exc()}")
        else:
            try:
                self.createPost(self.channels[channel], content)
            except Exception as e:
                self.log.error(f"Error   : Cannot handle {module_name} message: {str(e)}\nTraceback: {traceback.format_exc()}")

    def findModules(self):
        try:
            sys.path.append(module_path)
            modules = {}
            for root, dirs, files in os.walk(module_path):
                for module in fnmatch.filter(files, "feed.py"):
                    module_name = root.split('/')[-1]
                    if options.debug:
                        self.log.info(f"Found    : {module_name} module ...")
                    if not module_name in modules:
                        modules[module_name] = {}
                    modules[module_name]['cache'] = f"{root}/{module_name}.cache"
            self.log.info(f"Starting : {len(modules)} module(s) ...")
            return modules
        except Exception as e:
            if options.debug:
                self.log.error(f"Error   : {str(e)}\nTraceback: {traceback.format_exc()}")
        finally:
            sys.path.remove(module_path)

    def onComplete(self, future):
        try:
            result = future.result()
        except Exception as e:
            if options.debug:
                self.log.error(f"Error   : {str(e)}\nTraceback: {traceback.format_exc()}")

    def runModules(self):
        while True:
            history = None
            try:
                success = 0
                failed = 0
                self.modules = self.findModules()
                self.feedmap = self.update_feedmap()
                with pebble.ThreadPool(max_workers=options.Modules['threads']) as pool:
                    futures = []
                    for module_name in self.modules:
                        if options.debug:
                            self.log.info(f"Starting : {module_name} module ...")
                        history = shelve.open(self.modules[module_name]['cache'], writeback=True)
                        future = pool.submit(self.runModule, module_name, history)
                        future.add_done_callback(self.onComplete)
                        futures.append([module_name, future])
                        if history:
                            history.sync()
                            history.close()
                    for module_name, future in futures:
                        try:
                            result = future.result(timeout=options.Modules['timeout'])
                            success += 1
                        except TimeoutError as e:
                            if options.debug:
                                self.log.error(f"Timeout : {module_name} module ...\nTraceback: {str(e)}\n{traceback.format_exc()}")
                            else:
                                self.log.info(f"Timeout  : {module_name} module ...")
                            failed += 1
                        except CancelledError as e:
                            if options.debug:
                                self.log.error(f"Canceled: {module_name} module ...\nTraceback: {str(e)}\n{traceback.format_exc()}")
                            else:
                                self.log.info(f"Canceled : {module_name} module ...")
                            failed += 1
                        except Exception as e:
                            if options.debug:
                                self.log.error(f"Error   : {module_name} module ...\nTraceback: {str(e)}\n{traceback.format_exc()}")
                            else:
                                self.log.info(f"Error    : {module_name} module ...")
                            failed += 1
                        finally:
                            if not future.done():
                                future.cancel()
            except Exception as e:
                if options.debug:
                    self.log.error(f"Error   :{str(e)}\nTraceback: {traceback.format_exc()}")
                else:
                    self.log.error(f"Error   :{str(e)}")
                failed += 1
            finally:
                if history:
                    history.sync()
                    history.close()
                pool.stop()
                pool.join()
            self.log.info(f"Finished : {success}/{failed+success} modules ran successfully, sleeping {options.Modules['timer']} seconds ...")
            time.sleep(options.Modules['timer'])

    def runModule(self, module_name, history):
        try:
            if not module_name in history:
                history[module_name] = []
                first_run = True
            else:
                first_run = False
            if options.debug:
                self.log.info(f"Found    : {module_name} post history cache ...")
            items = self.callModule(module_name)
            if items:
                posts = []
                for newspost in items:
                    try:
                        channel, content, uploads = newspost
                    except:
                        channel, content = newspost
                        uploads = []
                    if not [channel, content, uploads] in posts:
                        posts.append([channel, content, uploads])
                    for extrachannel in self.feedmap[module_name]:
                        if not [extrachannel, content, uploads] in posts:
                            posts.append([extrachannel, content, uploads])
                for post in posts:
                    channel, content, uploads = post
                    # Make sure we're not triggering self-calls
                    if not content.startswith('@') and not content.startswith('!'):
                        if not first_run:
                            if not post in history[module_name]:
                                try:
                                    if not options.debug:
                                        self.log.info(f"Posting  : {module_name} => {channel} => {content.replace('\n','. ')[:40]} ...")
                                        self.handleMsg(channel, module_name, content, uploads)
                                    else:
                                        self.log.info(f"DbgMsg   : {module_name} => {channel} => {content.replace('\n','. ')[:40]} ...")
                                except Exception as e:
                                    if options.debug:
                                        self.log.error(f"Error   : {module_name}\nTraceback: {str(e)}\n{traceback.format_exc()}")
                        if not post in history[module_name]:
                            if not options.debug:
                                history[module_name].append(post)
                            else:
                                self.log.info(f"DbgCache : {module_name} => {channel} => {content.replace('\n','. ')[:40]} ...")
            if options.debug:
                self.log.info(f"Complete : {module_name} module ...")
        except Exception as e:
            if options.debug:
                self.log.error(f"Error   : {module_name} ...\nTraceback: {traceback.format_exc()}")

    def callModule(self, module_name, function_name = 'query', *args, **kwargs):
        spec = None
        try:
            importlib.invalidate_caches()
            module_file = os.path.join(module_path, module_name, "feed.py")
            if not os.path.exists(module_file):
                raise ImportError(f"No feed.py found for {module_name} ...")
            unique_module_name = f"feed_{uuid.uuid4().hex}"
            spec = importlib.util.spec_from_file_location(unique_module_name, module_file)
            if not spec or spec.loader is None:
                raise ImportError(f"Could not load spec for {module_file} ...")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                raise ImportError(f"Module {module_name} could not be executed...")
            func = getattr(module, function_name)
            if not callable(func):
                raise AttributeError(f"{function_name} is not callable in {module_name} ...")
            return func(*args, **kwargs)
        except Exception as e:
            if options.debug:
                self.log.error(f"Error   :{str(e)}\nTraceback: {traceback.format_exc()}")
            return None
        finally:
            if spec and spec.name in sys.modules:
                del sys.modules[spec.name]
                if options.debug:
                    self.log.info(f"Unloaded : {module_name} ({spec.name}) module ...")


def main(log):
    mm = MattermostManager(log)
    try:
        mm.runModules()
    except Exception as e:
        if options.debug:
            self.log.error(f"Error   :{str(e)}\nTraceback: {traceback.format_exc()}")

if __name__ == '__main__' :
    '''
    Interactive run from the command-line
    '''
    parser = configargparse.ArgParser(config_file_parser_class=configargparse.YAMLConfigFileParser,
                                      description='Matterfeed loads modules '
                                                  'and sends their output '
                                                  'to Mattermost.',
                                                  default_config_files=['config.yaml'])
    parser.add('--Matterbot', type=str, help='Matterfeed configuration, as a dictionary (see YAML config)')
    parser.add('--Modules', type=str, help='Modules configuration, as a dictionary (see YAML config)')
    parser.add('--debug', default=False, action='store_true', help='Enable debug mode and log to foreground')
    options, unknown = parser.parse_known_args()
    options.Matterbot = ast.literal_eval(options.Matterbot)
    options.Modules = ast.literal_eval(options.Modules)
    if not options.debug:
        logging.basicConfig(level=logging.INFO, filename=options.Matterbot['logfile'], format='%(levelname)s - %(name)s - %(asctime)s - %(message)s')
    else:
        logging.basicConfig(level=logging.DEBUG,format='%(levelname)s - %(name)s - %(asctime)s - %(message)s')
    log = logging.getLogger('MatterFeed')
    log.info('>>> Starting matterfeed ...')
    if options.debug:
        log.info('>>> WARNING: debug logging enabled ...')
    else:
        log.info('>>> Debug logging disabled ...')
    try:
        current_dir = os.path.dirname(__file__)
        module_path = options.Modules['moduledir'].strip('/')
        main(log)
    except KeyboardInterrupt:
        log.info('<<< Stopping matterfeed ...')
        sys.exit(0)
