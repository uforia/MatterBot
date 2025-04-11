#!/usr/bin/env python3

import ast
from concurrent.futures import TimeoutError
import configargparse
import fnmatch
import importlib.util
import logging
import multiprocessing
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
        self.modules = self.findModules()
        userchannels = self.mmDriver.channels.get_channels_for_user(self.me['id'],self.my_team_id)
        for userchannel in userchannels:
            channel_info = self.mmDriver.channels.get_channel(userchannel['id'])
            self.channels[channel_info['name']] = channel_info['id']
    
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
            self.log.error(f"An error posting a channel message:\nError: {str(e)}\n{traceback.format_exc()}")

    def handleMsg(self, channel, module_name, content, uploads = None):
        self.log.info('Message  : ' + module_name.lower() + ' => ' + channel + ' => ' + content[:20] + '...')
        if uploads:
            try:
                self.createPost(self.channels[channel], content, uploads)
            except Exception as e:
                self.log.error('Error   : ' + module_name + f"\nTraceback: {str(e)}\n{traceback.format_exc()}")
        else:
            try:
                self.createPost(self.channels[channel], content)
            except Exception as e:
                self.log.error('Error   : ' + module_name + f"\nTraceback: {str(e)}\n{traceback.format_exc()}")

    def findModules(self):
        try:
            sys.path.append(module_path)
            modules = {}
            for root, dirs, files in os.walk(module_path):
                for module in fnmatch.filter(files, "feed.py"):
                    module_name = root.split('/')[-1]
                    self.log.info(f"Found    : {module_name} module...")
                    if not module_name in modules:
                        modules[module_name] = {}
                    modules[module_name]['cache'] = f"{root}/{module_name}.cache"
            return modules
        except Exception as e:
            self.log.error(f"Error   :\nTraceback: {str(e)}\n{traceback.format_exc()}")
        finally:
            sys.path.remove(module_path)

    def onComplete(self, future):
        try:
            result = future.result()
        except Exception as e:
            self.log.error(f"Error   :\nTraceback: {str(e)}\n{traceback.format_exc()}")

    def runModules(self):
        while True:
            try:
                self.modules = self.findModules()
                with pebble.ThreadPool(max_workers=8) as pool:
                    history = None
                    futures = []
                    for module_name in self.modules:
                        self.log.info(f"Starting : {module_name} module...")
                        history = shelve.open(self.modules[module_name]['cache'], writeback=True)
                        future = pool.submit(self.runModule, module_name, history)
                        future.add_done_callback(self.onComplete)
                        futures.append([module_name, future])
                    for module_name, future in futures:
                        try:
                            result = future.result(timeout=30)
                        except Exception as e:
                            self.log.error(f"Timeout : {module_name}\nTraceback: {str(e)}\n{traceback.format_exc()}")
            except Exception as e:
                self.log.error(f"Error   :\nTraceback: {str(e)}\n{traceback.format_exc()}")
            finally:
                if history:
                    history.sync()
                    history.close()
                pool.stop()
                pool.join()
            self.log.info(f"Run complete, sleeping for {options.Modules['timer']} seconds...")
            time.sleep(options.Modules['timer'])

    def runModule(self, module_name, history):
        try:
            if not module_name in history:
                history[module_name] = []
                first_run = True
            else:
                first_run = False
            self.log.info('Found    : ' + module_name + ' cache ...')
            items = self.callModule(module_name)
            if items:
                for newspost in items:
                    try:
                        channel, content, uploads = newspost
                    except:
                        channel, content = newspost
                        uploads = []
                    # Make sure we're not triggering self-calls...
                    if not content.startswith('@') and not content.startswith('!'):
                        if not first_run:
                            if not newspost in history[module_name]:
                                try:
                                    self.log.info('Posting  : ' + module_name + ' => ' + channel + ' => ' + content[:80] + '...')
                                    self.handleMsg(channel, module_name, content, uploads)
                                except Exception as e:
                                    self.log.error('Error   : ' + module_name + f"\nTraceback: {str(e)}\n{traceback.format_exc()}")
                        if not newspost in history[module_name]:
                            history[module_name].append(newspost)
                            self.log.info('Storing  : ' + module_name + ' => ' + channel + ' => ' + content[:80] + '...')
            self.log.info('Complete : ' + module_name + ' => sleeping ...')
        except Exception as e:
            self.log.error(f"Error   : {module_name}\nTraceback: {str(e)}\n{traceback.format_exc()}")

    def callModule(self, module_name, function_name = 'query', *args, **kwargs):
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
            spec.loader.exec_module(module)
            func = getattr(module, function_name)
            return func(*args, **kwargs)
        except (ModuleNotFoundError, AttributeError) as e:
            self.log.error(f"Error   :\nTraceback: {str(e)}\n{traceback.format_exc()}")
            return None
        finally:
            if spec.name in sys.modules:
                del sys.modules[spec.name]
                self.log.info(f"Unloaded : {module_name} ({spec.name}) module ...")


def main(log):
    mm = MattermostManager(log)
    try:
        mm.runModules()
    except Exception as e:
        log.error(f"Traceback: {str(e)}\n{traceback.format_exc()}")

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
    log = logging.getLogger('MatterAPI')
    log.info('Starting MatterFeed')
    try:
        current_dir = os.path.dirname(__file__)
        module_path = options.Modules['moduledir'].strip('/')
        main(log)
    except KeyboardInterrupt:
        log.info('Stopping MatterFeed')
        sys.exit(0)
