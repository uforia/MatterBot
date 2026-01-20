#!/usr/bin/env python3

import json
import requests
import re
import traceback

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

# Function to validate a domain name using regex
def is_valid_domain(domain):
    # Regular expression to validate a domain name
    domain_regex = r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+(?:[A-Za-z]{2,})$"
    return bool(re.match(domain_regex, domain))


def process(command, channel, username, params, files, conn):
    messages = []
    param = params[0] if params else None
    # Validate the input parameter as a valid IP address
    if is_valid_domain(param):
        try:
            # API URL for fetching data
            headers = {
                'Content-Type': settings.CONTENTTYPE,
                'User-Agent': 'MatterBot integration for crtsh v0.1'
            }
            api_url = f"{settings.APIURL['crtsh']['url']}{param}"
            # Request data from the API
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()  # Ensure we raise an error for bad status codes
            json_response = response.json()
            if len(json_response):
                table_message = ""
                unique_common_names = set()
                # Create the header of the table
                table_message += f"Here are the last `{settings.ENTRIES}` crt.sh results for: `{param}`\n\n"
                table_message += "| Issuer Name     | Common Name     | Entry Time      | Validity        |\n"
                table_message += "|-----------------|-----------------|-----------------|-----------------|\n"
                table_message += "|||| |\n"
                # Iterate through entries in the JSON response
                length = 0
                for entry in sorted(json_response, key=lambda x: x['entry_timestamp'], reverse=True):
                    common_name = entry.get('common_name')
                    if common_name and common_name not in unique_common_names:
                        unique_common_names.add(common_name)
                        issuer_name = entry.get('issuer_name', 'Unknown Issuer')
                        entry_timestamp = entry.get('entry_timestamp', 'N/A')
                        not_before = entry.get('not_before', 'N/A')
                        not_after = entry.get('not_after', 'N/A')
                        # Add a row for each entry in the table
                        table_message += (
                            f"| `{issuer_name}`     | `{common_name}`    | `{entry_timestamp}` | `{not_before}` to `{not_after}` |\n"
                        )
                        length += 1
                        if length == settings.ENTRIES:
                            break
                messages.append({'text': table_message.strip()})
        except Exception as e:
            # Append error message to the messages list
            messages.append({'text': 'An error occurred in crtsh:\nError: ' + (str(e),traceback.format_exc())})
        finally:
            # Return the messages list
            return {'messages': messages}
