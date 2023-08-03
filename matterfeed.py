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
from mattermostdriver import Driver

class TokenAuth(requests.auth.AuthBase):
    def __call__(self, r):
        r.headers['Authorization'] = "Bearer %s" % options.Matterbot['password']
        r.headers['X-Requested-With'] = "XMLHttpRequest"
        return r

class MattermostManager(object):
    def __init__(self):
        logQueue.put(('INFO', "Going to set up driver for connection to %s " % (options.Matterbot['host'],) ))
        self.mmDriver = Driver(options={
            'url'       : options.Matterbot['host'],
            'scheme'    : 'https',
            'port'      : options.Matterbot['port'],
            'auth'      : TokenAuth,
            'basepath'  : '/api/v4',
            'debug'     : options.debug,
        })
        self.me = self.mmDriver.users.get_user( user_id='me' )
        self.my_team_id = self.mmDriver.teams.get_team_by_name(options.Matterbot['teamname'])['id']
        self.channels = {}
        self.test = {}
        userchannels = self.mmDriver.channels.get_channels_for_user(self.me['id'],self.my_team_id)
        for userchannel in userchannels:
            channel_info = self.mmDriver.channels.get_channel(userchannel['id'])
            self.channels[channel_info['name']] = channel_info['id']

    def createPost( self, channel, content) :
        self.mmDriver.posts.create_post( options={'channel_id': channel,
                                                  'message': content,
                                                  })

def postMsg():
    logQueue.put(('INFO', 'Connecting to Mattermost ...'))
    history = {}
    logQueue.put(('INFO', 'Monitoring message queue ...'))
    while True:
        newsItem = msgQueue.get()
        channel, module, content = newsItem
        logQueue.put(('INFO', 'Message: ' + module.lower() + ' => ' + mm.channels[channel] + ' => ' + content[:20] + '...'))
        mm.createPost(mm.channels[channel], content)
        msgQueue.task_done()

def logger():
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
        logItem = logQueue.get()
        logLevel, logText = logItem
        if logLevel.upper() == 'INFO':
            log.info(logText)
        elif logLevel.upper() == 'ERROR':
            log.error(logText)
        elif logLevel.upper() == 'DEBUG':
            log.debug(logText)
        else:
            log.info('Unhandled log entry: ' + logText)
        logQueue.task_done()

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
        if options.debug:
            logQueue.put(('DEBUG', 'Creating: ' + self.module + ' window of ' + str(options.Modules['window']) + ' entries...'))
        try:
            items = modules[self.module](options.Modules['window'])
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

    # Logging thread
    logQueue = queue.Queue()
    logThread = threading.Thread(target=logger).start()
    logQueue.put(('INFO', 'Log thread started ...'))

    # Mattermost post connection
    mm = MattermostManager()

    # Channel message handler
    msgQueue = queue.Queue()
    postThread = threading.Thread(target=postMsg).start()
    logQueue.put(('INFO', 'Message thread started ...'))

    # Find and load all modules concurrently, and build a lookback history
    modules = loadModules()
    history = {}
    if len(modules)<=0:
        logQueue.put(('ERROR'), 'No modules found - exiting!')
        sys.exit(1)

    # Schedule the module polling and run forever
    threads = []
    for module in modules:
        thread = ModuleWorker(mm, module, logQueue, msgQueue)
        threads.append(thread)
        thread.start()

    while len(threads)>0:
        try:
            threads = [t.join(1) for t in threads if t is not None and t.is_alive()]
        except KeyboardInterrupt:
            logQueue.put(('INFO', 'Shutting down all workers and exiting ...'))
            if logThread is not None and logThread.is_alive():
                logThread.join()
            if postThread is not None and postThread.is_alive():
                postThread.join()
            for thread in threads:
                thread.kill_received = True
    sys.exit(0)
