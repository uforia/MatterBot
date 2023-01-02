#!/usr/bin/env python3

import logging
import requests
import threading
import queue
import time
import datetime
import os
import sys
import fnmatch
import importlib.util
import concurrent.futures
import configargparse
import ast
import asyncio
import json

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
        for channel in options.Matterbot['channelmap']:
            self.channels[channel] = self.mmDriver.channels.get_channel_by_name(self.my_team_id, options.Matterbot['channelmap'][channel])['id']

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
        mm.createPost(mm.channels[channel], module.lower() + ' => ' + content)
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

def runModule(mm, module, logQueue, msgQueue, history, first_run=False):
    logQueue.put(('INFO', 'Starting : ' + module.lower()))
    items = modules[module](options.Modules['window'])
    if items:
        for item in items:
            channel, content = item
            if first_run:
                history[module].append(item)
                if options.debug:
                    logQueue.put(('DEBUG', 'Storing : ' + module + ' => ' + channel + ' => ' + content[:20] + '...'))
            else:
                if not item in history[module]:
                    history[module].append(item)
                    if options.debug:
                        logQueue.put(('DEBUG', 'Posting : ' + module + ' => ' + channel + ' => ' + content[:20] + '...'))
                    msgQueue.put((channel, module.title(), content))
                else:
                    if options.debug:
                        logQueue.put(('DEBUG', 'Ignoring: ' + module + ' => ' + channel + ' => ' + content[:20] + '...'))
        if options.debug:
            logQueue.put(('DEBUG', 'Summary : ' + module + ' => '+ str(len(items)) + ' messages ...'))
    logQueue.put(('INFO', 'Completed: ' + module))

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
    if len(modules) > 0:
        threads = {}
        for module in modules:
            history[module] = []
            threads[module] = threading.Thread(target=runModule, args=(mm, module, logQueue, msgQueue, history, True))
            threads[module].start()
    else:
        logQueue.put(('ERROR'), 'No modules found - exiting!')
        sys.exit(1)
    for thread in threads:
        threads[thread].join()
    first_run = False

    # Schedule the module polling and run forever
    try:
        while True:
            time.sleep(options.Modules['timer'])
            if len(modules) > 0:
                threads = {}
                for module in modules:
                    threads[module] = threading.Thread(target=runModule, args=(mm, module, logQueue, msgQueue, history, False))
                    threads[module].start()
            else:
                logQueue.put(('ERROR'), 'No modules found - exiting!')
                sys.exit(1)
    except KeyboardInterrupt:
        logQueue.put(('INFO', 'Shutting down all workers and exiting ...'))
        for module in threads:
            threads[module].join()
