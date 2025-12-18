#!/usr/bin/env python3

import collections
import json
import re
import requests
import traceback
import urllib.parse
from pathlib import Path
try:
    from commands.urlscan import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('commands/urlscan/settings.py').is_file():
        try:
            from commands.urlscan import settings
        except ModuleNotFoundError: # local test run
            import settings

def process(command, channel, username, params, files, conn):
    if len(params)>0:
        messages = []
        params = [_.replace('[', '').replace(']', '').replace('hxxp','http') for _ in params]
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'api-key': settings.APIURL['urlscan']['key'],
        }
        try:
            pattern = r"\b(?:[a-zA-Z0-9-]+\.)+(?:[a-zA-Z]{2,}|xn--[a-zA-Z0-9-]+)\b"
            hostnames = re.findall(pattern, " ".join(params))
            for hostname in hostnames:
                query = {
                    "q": f"domain:{hostname}",
                    "size": settings.ENTRIES,
                    "datasource": "scans",
                }
                with requests.get(settings.APIURL['urlscan']['url'], headers=headers, params=query) as response:
                    if response.status_code in (400,):
                        message = "Incorrect Urlscan query!"
                    elif response.status_code in (401,):
                        message = "Incorrect Urlscan API key or not configured!"
                    else:
                        json_response = response.json()
                        if "results" in json_response:
                            if len(json_response["results"]):
                                length = 0
                                message = "Urlscan.io search results for: `"+"`, `".join(params)+"`\n"
                                message += f"\n| Timestamp | Title | IP | URL | Verdict | Details | Screenshot |"
                                message += f"\n| -: | :- | -: | :- | :- |"
                                fields = ['title', 'ip', 'url']
                                for result in json_response["results"]:
                                    if "task" in result:
                                        if "url" in result["task"]:
                                            if any(_ in result["task"]["url"] for _ in params):
                                                time = result["task"]["time"]
                                                message += f"\n| {time} "
                                                for field in fields:
                                                    if field in result['page']:
                                                        message += f"| `{result['page'][field].replace('.','[.]',1).replace(':','[:]',1).replace('http','hxxp').replace('|','-')}` "
                                                    else:
                                                        message += f"| - "
                                                verdicturl = result["result"]
                                                with requests.get(verdicturl, headers=headers) as verdictresponse:
                                                    if not response.status_code in (200, 206):
                                                        messages.append({'text': "An error occurred retrieving Urlscan details"})
                                                    else:
                                                        json_verdict = verdictresponse.json()
                                                        if "verdicts" in json_verdict:
                                                            if "overall" in json_verdict["verdicts"]:
                                                                if "malicious" in json_verdict["verdicts"]["overall"]:
                                                                    malicious = json_verdict["verdicts"]["overall"]["malicious"]
                                                                    if not malicious:
                                                                        message += "| Safe "
                                                                    else:
                                                                        message += "| *MALICIOUS* "
                                                details = verdicturl.replace('api/v1/','')
                                                screenshot = result["screenshot"]
                                                message += f"| [Details]({details}) | [Screenshot]({screenshot}) "
                                                message += "|"
                                                length += 1
                                message += "\n\n"
                                if length>0:
                                    messages.append({'text': message})
        except Exception as e:
            messages.append({'text': 'A Python error occurred searching Urlscan: %s\n%s' % (str(e),traceback.format_exc())})
        finally:
            return {'messages': messages}
