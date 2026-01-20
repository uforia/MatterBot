#!/usr/bin/env python3

# Every module must set the CHANNELS variable to indicate where information should be sent to in Mattermost
#
# Every module must implement the query() function.
# This query() function is called by the main worker and has only one parameter: the number of historic
# items that should be returned in the list.
#
# Every module must return a list [...] with 0, 1 ... n entries
# of 2-tuples: ('<channel>', '<content>')
#
# <channel>: basically the destination channel in Mattermost, e.g. 'Newsfeed', 'Incident', etc.
# <content>: the content of the message, MD format possible

import datetime
import re
import requests
import shelve
import traceback
import unicodedata

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

def query(MAX=settings.ENTRIES):
    items = set()
    count = 0
    stripchars = r'\_\+\=\/\"\'\\\/'
    regex = re.compile('[%s]' % stripchars)
    headers = {
        'Content-Type': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for VARIoT v1.0',
    }
    try:
        if Path(settings.HISTORY).is_file():
            history = shelve.open(settings.HISTORY,writeback=True)
        else:
            if Path('modules/variot/'+settings.HISTORY).is_file():
                history = shelve.open('modules/variot/'+settings.HISTORY,writeback=True)
        if not Path(settings.HISTORY).is_file() and not Path('modules/variot/'+settings.HISTORY).is_file():
            if Path('feed.py').is_file():
                history = shelve.open(settings.HISTORY,writeback=True)
            else:
                if Path('modules/variot/feed.py').is_file():
                    history = shelve.open('modules/variot/'+settings.HISTORY,writeback=True)
        if not 'variot' in history:
            history['variot'] = []
    except Exception as e:
        print(traceback.format_exc())
        raise
    try:
        if history:
            session = requests.Session()
            before = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
            url = f"{settings.URL}?limit={settings.ENTRIES}&before={before}&since={since}"
            with session.get(url=url, headers=headers) as response:
                if response.status_code in (200,):
                    json_response = response.json()
        if 'results' in json_response:
            results = json_response['results']
            try:
                while count < settings.ENTRIES and count < len(results):
                    entry = results[count]
                    var = entry['id']
                    last_update = entry['last_update_date']
                    cve = entry['cve'] if 'cve' in entry else None
                    historyitem = (var,last_update)
                    if not historyitem in history['variot']:
                        description = regex.sub('',unicodedata.normalize('NFKD',entry['description']['data'])).strip().replace('\n','. ')
                        if len(description)>400:
                            description = description[:396]+" ..."
                        link = f"https://www.variotdbs.pl/vuln/{var}/"
                        if 'cvss' in entry:
                            cvssv2 = entry['cvss']['data'][0]['cvssV2'][0]['baseScore'] if len(entry['cvss']['data'][0]['cvssV2']) else None
                            cvssv3 = entry['cvss']['data'][0]['cvssV3'][0]['baseScore'] if len(entry['cvss']['data'][0]['cvssV3']) else None
                            severity = entry['cvss']['data'][0]['severity'][0]['value'] if len(entry['cvss']['data'][0]['severity']) else None
                        else:
                            cvssv2 = None
                            cvssv3 = None
                            severity = None
                        content = settings.NAME + f": [{var}]({link}) "
                        if cve:
                            content += f"- CVE: `{cve}`"
                        if cvssv2:
                            content += f"- CVSSv2: `{cvssv2}`"
                        if cvssv3:
                            content += f"- CVSSv3: `{cvssv3}`"
                        if severity:
                            content += f"- Severity: `{severity}`"
                        content += f"\n>{description}\n"
                        for channel in settings.CHANNELS:
                            items.add((channel, content))
                        history['variot'].append(historyitem)
                    count += 1
            except IndexError:
                return items # No more items
            except Exception as e:
                print(traceback.format_exc())
            return items
    except Exception as e:
        print(traceback.format_exc())
    return items

if __name__ == "__main__":
    for item in query():
        print(item)
