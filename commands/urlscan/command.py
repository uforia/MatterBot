#!/usr/bin/env python3

import concurrent.futures
import re
import requests
import traceback
from concurrent.futures import ThreadPoolExecutor

### Dynamic configuration loader (do not change/edit)
from importlib import import_module
from types import SimpleNamespace
from pathlib import Path
_pkg = __package__ or Path(__file__).parent.name
def _load(module_name):
    try:
        return import_module(f".{module_name}", package=_pkg)
    except ModuleNotFoundError:
        try:
            return import_module(module_name)
        except ModuleNotFoundError:
            return None
_defaults = _load("defaults")
_settings = _load("settings")
_settings_dict = {
    k: v
    for mod in (_defaults, _settings)
    if mod
    for k, v in vars(mod).items()
    if not k.startswith("__")
}
settings = SimpleNamespace(**_settings_dict)
### Loader end, actual module functionality starts here
 
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
                with requests.get(settings.APIURL['urlscan']['url'], headers=headers, params=query, timeout=(10, 30)) as response:
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
                                candidates = []
                                for result in json_response["results"]:
                                    if "task" in result:
                                        if "url" in result["task"]:
                                            if any(_ in result["task"]["url"] for _ in params):
                                                time = result["task"]["time"]
                                                fields_text = ""
                                                for field in fields:
                                                    if field in result['page']:
                                                        fields_text += f"| `{result['page'][field].replace('.','[.]',1).replace(':','[:]',1).replace('http','hxxp').replace('|','-')}` "
                                                    else:
                                                        fields_text += f"| - "
                                                verdicturl = result["result"]
                                                details = verdicturl.replace('api/v1/','')
                                                screenshot = result["screenshot"]
                                                candidates.append((time, fields_text, verdicturl, details, screenshot))
                                verdict_results = {}
                                if candidates:
                                    def _fetch_verdict(url):
                                        try:
                                            with requests.get(url, headers=headers, timeout=(10, 30)) as r:
                                                return r.json()
                                        except Exception:
                                            return None

                                    pool = ThreadPoolExecutor(max_workers=min(len(candidates), 6))
                                    try:
                                        future_to_idx = {pool.submit(_fetch_verdict, c[2]): i for i, c in enumerate(candidates)}
                                        done, _not_done = concurrent.futures.wait(list(future_to_idx.keys()), timeout=25)
                                        for fut in done:
                                            verdict_results[future_to_idx[fut]] = fut.result()
                                    finally:
                                        pool.shutdown(wait=False, cancel_futures=True)
                                for i, (time, fields_text, verdicturl, details, screenshot) in enumerate(candidates):
                                    message += f"\n| {time} "
                                    message += fields_text
                                    json_verdict = verdict_results.get(i)
                                    if json_verdict and "verdicts" in json_verdict:
                                        if "overall" in json_verdict["verdicts"]:
                                            if "malicious" in json_verdict["verdicts"]["overall"]:
                                                malicious = json_verdict["verdicts"]["overall"]["malicious"]
                                                if not malicious:
                                                    message += "| Safe "
                                                else:
                                                    message += "| *MALICIOUS* "
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
