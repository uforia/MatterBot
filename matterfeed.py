#!/usr/bin/env python3

import ast
import multiprocessing.context
import configargparse
import fnmatch
import importlib.util
import logging
import multiprocessing
import requests
import os
import shelve
import sys
import time
import traceback
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

    def handleMsg(self, channel, modulename, content, uploads = None):
        self.log.info('Message  : ' + modulename.lower() + ' => ' + channel + ' => ' + content[:20] + '...')
        if uploads:
            try:
                self.createPost(self.channels[channel], content, uploads)
            except:
                self.log.error('Error    : ' + modulename + f"\nTraceback: {str(e)}\n{traceback.format_exc()}")

        else:
            try:
                self.createPost(self.channels[channel], content)
            except:
                self.log.error('Error    : ' + modulename + f"\nTraceback: {str(e)}\n{traceback.format_exc()}")

    def findModules(self):
        try:
            sys.path.append(module_path)
            modules = set()
            for root, dirs, files in os.walk(module_path):
                for module in fnmatch.filter(files, "feed.py"):
                    module_name = root.split('/')[-1]
                    self.log.info(f"Discovered the {module_name} module...")
                    modules.add(module_name)
            return modules
        except Exception as e:
            self.log.error(f"Error    :\nTraceback: {str(e)}\n{traceback.format_exc()}")
        finally:
            sys.path.remove(module_path)

    def runModules(self):
        while True:
            try:
                with multiprocessing.Pool(len(self.modules)) as pool:
                    modulelist = []
                    for modulename in self.modules:
                        self.log.info(f"Attempting to start the {modulename} module...")
                        m = pool.apply_async(self.runModule, [modulename, self.log])
                        modulelist.append(m)
                    results = []
                    for m in modulelist:
                        result = None
                        try:
                            result = m.get(timeout=options.Modules['timeout'])
                        except multiprocessing.context.TimeoutError as e:
                            self.log.error(f"Error   : {modulename} timed out during execution ...")
                        if result:
                            results.append(result)
            except Exception as e:
                self.log.error(f"Error    :\nTraceback: {str(e)}\n{traceback.format_exc()}")
            finally:
                pool.close()
                pool.terminate()
            self.log.info(f"Run complete, sleeping for {options.Modules['timer']} seconds...")
            time.sleep(options.Modules['timer'])

    def callModule(self, module_name, function_name = 'query', *args, **kwargs):
        try:
            importlib.invalidate_caches()
            sys.path.append(f"{module_path}/{module_name}")
            module = importlib.import_module("feed")
            func = getattr(module, function_name)
            return func(*args, **kwargs)
        except (ModuleNotFoundError, AttributeError) as e:
            self.log.error(f"Error    :\nTraceback: {str(e)}\n{traceback.format_exc()}")
            return None
        finally:
            sys.path.remove(f"{module_path}/{module_name}")
            if module_name in sys.modules:
                del sys.modules[module_name]

    def runModule(self, modulename, log):
        self.log = log
        try:
            items = self.callModule(modulename)
            self.historypath = options.Modules['moduledir']+'/'+modulename+'/'+modulename+'.cache'
            if os.path.isfile(self.historypath):
                if options.debug:
                    self.log.debug('Found   : ' + modulename + ' database at ' + self.historypath + ' location...')
            try:
                with shelve.open(self.historypath, writeback=True) as history:
                    if not modulename in history:
                        history[modulename] = []
                        first_run = True
                    else:
                        first_run = False
                    if len(items):
                        for newspost in items:
                            try:
                                channel, content, uploads = newspost
                            except:
                                channel, content = newspost
                                uploads = []
                            # Deal with self-calls...
                            if content.startswith('@') or content.startswith('!'):
                                if not first_run:
                                    if options.debug:
                                        self.log.debug('Posting  : ' + modulename + ' => ' + channel + ' => ' + content + '...')
                                    else:
                                        self.log.info('Posting  : ' + modulename + ' => ' + channel + ' => ' + content[:80] + '...')
                                        try:
                                            self.handleMsg(channel, modulename, content, uploads)
                                        except:
                                            self.log.error('Error    : ' + modulename + f"\nTraceback: {str(e)}\n{traceback.format_exc()}")
                            elif not newspost in history[modulename]:
                                history[modulename].append(newspost)
                                history.sync()
                                history.close()
                                if not first_run:
                                    if options.debug:
                                        self.log.debug('Posting  : ' + modulename + ' => ' + channel + ' => ' + content + '...')
                                    else:
                                        self.log.info('Posting  : ' + modulename + ' => ' + channel + ' => ' + content[:80] + '...')
                                        try:
                                            self.handleMsg(channel, modulename, content, uploads)
                                        except:
                                            self.log.error('Error    : ' + modulename + f"\nTraceback: {str(e)}\n{traceback.format_exc()}")
                    if options.debug:
                        self.log.debug('Summary : ' + modulename + ' => '+ str(len(items)) + ' messages ...')
                self.log.info('Completed: ' + modulename + ' => sleeping ...')
            except Exception as e:
                self.log.error('Error    : ' + modulename + f"\nTraceback: {str(e)}\n{traceback.format_exc()}")
            finally:
                history.sync()
                history.close()
        except Exception as e:
            self.log.error('Error    : ' + modulename + f"\nTraceback: {str(e)}\n{traceback.format_exc()}")


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
