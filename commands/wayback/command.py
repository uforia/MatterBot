#!/usr/bin/env python3

import datetime
import re
import requests
import traceback

### Dynamic configuration loader (do not change/edit)
import importlib
from pathlib import Path
_pkg_name = Path(__file__).parent.name
try:
    defaults_mod = importlib.import_module(f'commands.{_pkg_name}.defaults')
except ModuleNotFoundError:
    try:
        defaults_mod = importlib.import_module('defaults')
    except ModuleNotFoundError:
        print(f"Module {_pkg_name} could not be loaded due to a missing default configuration.")
try:
    settings_mod = importlib.import_module(f'commands.{_pkg_name}.settings')
except ModuleNotFoundError:
    try:
        settings_mod = importlib.import_module('settings')
    except ModuleNotFoundError:
        settings_mod = None
settings = {k: v for k, v in vars(defaults_mod).items() if not k.startswith('__')}
if settings_mod:
    settings.update({k: v for k, v in vars(settings_mod).items() if not k.startswith('__')})
from types import SimpleNamespace
settings = SimpleNamespace(**settings)
### Loader end, actual module functionality starts here

def process(command, channel, username, params, files, conn):
    # Methods to query the current API account info (credits etc.)
    stripchars = '`\n\r\'\"'
    regex = re.compile('[%s]' % stripchars)
    messages = []
    headers = {
        'Content-Type': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for Wayback Machine v1.0',
    }
    try:
        if len(params):
            query = params[0]
            if ('http' and '://') in query:
                host = query.replace('[.]','.').replace('http://','').replace('https://','')
                if re.search(r"^(((?!\-))(xn\-\-)?[a-z0-9\-_]{0,61}[a-z0-9]{1,1}\.)*(xn\-\-)?([a-z0-9\-]{1,61}|[a-z0-9\-]{1,30})\.[a-z]{2,}$", host):
                    session = requests.Session()
                    url = settings.APIURL['wayback']['url']+f"{query}"
                    with session.get(url=url, headers=headers) as response:
                        if response.status_code in (200,):
                            json_response = response.json()
                            if 'archived_snapshots' in json_response:
                                if len(json_response['archived_snapshots']):
                                    closest = json_response['archived_snapshots']['closest']
                                    status = closest['status']
                                    available = ":large_green_circle:" if closest['available'] else ":red_circle:"
                                    url = closest['url']
                                    rawtimestamp = closest['timestamp']
                                    timestamp = datetime.datetime.strptime(rawtimestamp, "%Y%m%d%H%M%S").strftime("%B %d, %Y at %H:%M:%S UTC")
                                    message = f"| Wayback Machine result | `{query}` |\n"
                                    message += "| :- | -: |\n"
                                    message += f"| **Available** | {available} |\n"
                                    message += f"| **HTTP Status** | `{status}` |\n"
                                    message += f"| **Newest Snapshot Time** | `{timestamp}` |\n"
                                    message += f"| **Newest Snapshot Link** | [Wayback Machine]({url}) |\n"
                                    url = settings.APIURL['wayback']['cdx']+f"{query}"
                                    with session.get(url=url, headers=headers) as response:
                                        if response.status_code in (200,):
                                            cdxlist = response.content.split(b'\n')
                                            snapshotcount = len(cdxlist)
                                            oldestentry = cdxlist[0]
                                            cdxfields = oldestentry.split(b' ')
                                            rawtimestamp = cdxfields[1].decode('utf-8')
                                            timestamp = datetime.datetime.strptime(rawtimestamp, "%Y%m%d%H%M%S").strftime("%B %d, %Y at %H:%M:%S UTC")
                                            url = f"http://web.archive.org/web/{rawtimestamp}/{query}"
                                            message += f"| **Oldest Snapshot Time** | `{timestamp}` |\n"
                                            message += f"| **Oldest Snapshot Link** | [Wayback Machine]({url}) |\n"
                                            message += f"| **Number Of Snapshots** | {snapshotcount} |\n"
                                    message += "\n\n"
                                    messages.append({'text': message})
                                else:
                                    messages.append({'text': f"URL `{query}` is not present in the archive.org's Wayback Machine."})
                else:
                    messages.append({'text': f"URL `{query}` is not valid for archive.org's Wayback Machine."})
    except:
        messages.append({'text': 'An error occurred in the Wayback Machine module:\nError: `%s`' % (traceback.format_exc(),)})
    finally:
        return {'messages': messages}