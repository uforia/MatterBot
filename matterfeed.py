#!/usr/bin/env python3

import ast
import configargparse
import fnmatch
import importlib.util
import logging
import requests
import os
import queue
import shelve
import sys
import threading
import time
import traceback
from mattermostdriver import Driver


class TokenAuth():
    def __call__(self, r):
        r.headers['Authorization'] = "Bearer %s" % options.Matterbot['password']
        r.headers['X-Requested-With'] = 'XMLHttpRequest'
        return r


class MattermostManager(object):
    def __init__(self):
        logQueue.put(('INFO', "Going to set up driver for connection to %s " % (options.Matterbot['host'],) ))
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
        userchannels = self.mmDriver.channels.get_channels_for_user(self.me['id'],self.my_team_id)
        for userchannel in userchannels:
            channel_info = self.mmDriver.channels.get_channel(userchannel['id'])
            self.channels[channel_info['name']] = channel_info['id']

    def createPost(self, channel, text):
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
                self.mmDriver.posts.create_post(options={'channel_id': channel,
                                                            'message': block,
                                                            })
        except:
            raise


class MsgWorker(threading.Thread):
    def __init__(self, mm, logQueue, msgQueue):
        threading.Thread.__init__(self)
        self.terminate = False
        self.mm = mm
        self.logQueue = logQueue
        self.msgQueue = msgQueue

    def HandleMsg(self):
        self.logQueue.put(('INFO', 'Starting PostMsg Worker ...'))
        while True:
            newsItem = self.msgQueue.get()
            channel, module, content = newsItem
            self.logQueue.put(('INFO', 'Message: ' + module.lower() + ' => ' + channel + ' => ' + content[:20] + '...'))
            self.mm.createPost(self.mm.channels[channel], content)
            self.msgQueue.task_done()

    def run(self):
        while not self.terminate:
            self.HandleMsg()


class LogWorker(threading.Thread):
    def __init__(self, logQueue):
        threading.Thread.__init__(self)
        self.terminate = False
        self.logQueue = logQueue

    def HandleLog(self):
        if not options.debug:
            logging.basicConfig(filename=options.Matterbot['logfile'], format='%(levelname)s - %(name)s - %(asctime)s - %(message)s')
        else:
            logging.basicConfig(format='%(levelname)s - %(name)s - %(asctime)s - %(message)s')
        log = logging.getLogger( 'MatterBot' )
        if options.debug:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)
        log.info('Starting up log thread ...')
        while True:
            logItem = self.logQueue.get()
            logLevel, logText = logItem
            if logLevel.upper() == 'INFO':
                log.info(logText)
            elif logLevel.upper() == 'ERROR':
                log.error(logText)
            elif logLevel.upper() == 'DEBUG':
                log.debug(logText)
            else:
                log.info('Unhandled log entry: ' + logText)
            self.logQueue.task_done()

    def run(self):
        while not self.terminate:
            self.HandleLog()


def loadModules():
    modules = {}
    modulepath = options.Modules['moduledir'].strip('/')
    sys.path.append(modulepath)
    for root, dirs, files in os.walk(modulepath):
        for module in fnmatch.filter(files, "feed.py"):
            module_name = root.split('/')[-1]
            logQueue.put(('INFO', 'Attempting to load the ' + module_name + ' module...'))
            module = importlib.import_module(module_name + '.' + 'feed')
            modules[module_name] = getattr(module, 'query')
    return modules


class ModuleWorker(threading.Thread):
    def __init__(self, mm, module, logQueue, msgQueue):
        threading.Thread.__init__(self)
        self.terminate = False
        self.mm = mm
        self.module = module
        self.logQueue = logQueue
        self.msgQueue = msgQueue

    def runModule(self):
        logQueue.put(('INFO', 'Starting : ' + self.module))
        try:
            items = modules[self.module]()
            modulepath = options.Modules['moduledir']+'/'+self.module+'/'+self.module+'.cache'
            if os.path.isfile(modulepath):
                if options.debug:
                    logQueue.put(('DEBUG', 'Found   : ' + self.module + ' database at ' + modulepath + ' location...'))
            with shelve.open(modulepath,writeback=True) as history:
                if not self.module in history:
                    history[self.module] = []
                    first_run = True
                else:
                    first_run = False
                if len(items):
                    for item in items:
                        if not item in history[self.module]:
                            channel, content = item
                            history[self.module].append(item)
                            if not first_run:
                                if options.debug:
                                    self.logQueue.put(('DEBUG', 'Posting : ' + self.module + ' => ' + channel + ' => ' + content + '...'))
                                else:
                                    self.logQueue.put(('INFO', 'Posting : ' + self.module + ' => ' + channel + ' => ' + content[:80] + '...'))
                                    self.msgQueue.put((channel, self.module, content))
                if options.debug:
                    logQueue.put(('DEBUG', 'Summary : ' + self.module + ' => '+ str(len(items)) + ' messages ...'))
                history.sync()
                history.close()
            logQueue.put(('INFO', 'Completed: ' + self.module + ' => sleeping for ' + str(options.Modules['timer']) + ' seconds ...'))
        except:
            logQueue.put(('ERROR', 'Error    : ' + self.module + ' => sleeping for ' + str(options.Modules['timer']) + ' seconds ...'))
        time.sleep(options.Modules['timer'])
    
    def run(self):
        while not self.terminate:
            self.runModule()


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
    threads = []

    # Start the Mattermost connection
    try:
        # Start the logging thread
        logQueue = queue.Queue()
        thread = LogWorker(logQueue)
        threads.append(thread)
        thread.start()
        logQueue.put(('INFO', 'Logging thread started ...'))

        # Fire up the Mattermost connection
        mm = MattermostManager()
        if mm:
            # Start the message handler
            msgQueue = queue.Queue()
            thread = MsgWorker(mm, logQueue, msgQueue)
            threads.append(thread)
            thread.start()
            logQueue.put(('INFO', 'Message thread started ...'))

            # Find and load all modules concurrently, and build a lookback history
            modules = loadModules()
            if len(modules):
                # Schedule the modules and run forever
                for module in modules:
                    thread = ModuleWorker(mm, module, logQueue, msgQueue)
                    threads.append(thread)
                    thread.start()

                while len(threads)>0:
                    try:
                        threads = [t.join(1) for t in threads if t is not None and t.is_alive()]
                    except KeyboardInterrupt:
                        logQueue.put(('INFO', 'Shutting down all workers and exiting ...'))
                        for thread in threads:
                            thread.terminate = True
            else:
                logQueue.put(('ERROR', 'No modules found - exiting!'))
        else:
            logQueue.put(('ERROR', 'Could not connect to Mattermost - exiting!'))
    except Exception as e:
        logQueue.put(('ERROR', 'Error occurred:\n%s' % (traceback.format_exc(),)))
    finally:
        logQueue.put(('INFO', 'Matterfeed main loop running ...'))
        sys.exit(0)
