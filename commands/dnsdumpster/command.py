#!/usr/bin/env python3

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

    if not params:
        return {'messages': [{'text': "No parameters provided."}]}
    
    param = params[0]
    param2 = params[1:]

    try:
        messages = []
        types_allowed = ['a', 'cname', 'mx', 'ns']

        if param2:
            param2 = [item.strip(',') for item in param2]
            matches = [item for item in param2 if item in types_allowed]
            faulty_items = [item for item in param2 if item not in types_allowed]
            if faulty_items:
                messages.append({'text': f"No such record type(s): `{', '.join(faulty_items)}`. Choose from `{', '.join(types_allowed)}`"})
                return
            types_allowed = matches

        # API URL for fetching data
        api_url = f"{settings.APIURL['dnsdumpster']['url']}{param}"

        # Request headers
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'X-API-Key': settings.APIURL['dnsdumpster']['key'],
            'User-Agent': 'MatterBot integration for dnsdumpster v1.0',
        }

        # Request data from the API
        response = requests.get(api_url, headers=headers)
        # Ensure we raise an error for bad status codes
        response.raise_for_status()
        # Assign response to variable
        json_response = response.json()
        
        # Function to handle dynamic data collection and flatten nested structures (like 'ips')
        def collect_data(data, record_type_data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in types_allowed:  # Filter valid record types
                        record_type_data[key] = record_type_data.get(key, [])
                        for item in value:
                            # Ensure that 'item' is a dictionary before calling .items()
                            if isinstance(item, dict):
                                row = {}
                                # Collect all keys in the item dynamically and add them to the row
                                for sub_key, sub_value in item.items():
                                    if sub_key == "ips" and isinstance(sub_value, list):
                                        # Flatten the 'ips' list, default in requests
                                        for ip_entry in sub_value:
                                            for ip_key, ip_value in ip_entry.items():
                                                row[ip_key] = ip_value
                                    elif sub_value not in [None, [], {}, '']:  # Only include non-empty values
                                        row[sub_key] = sub_value
                                if row:  # Append row if it has valid data
                                    record_type_data[key].append(row)
                            else:
                                # If 'item' is not a dictionary, log or handle it as needed
                                continue
                    else:
                        collect_data(value, record_type_data)


        # Function to generate markdown table from collected row data
        def generate_markdown_table(record_type, record_data, excluded_headers=None):
            if not record_data:
                return ""  # Skip empty tables

            # Default to empty list if no excluded headers are specified
            if excluded_headers is None:
                excluded_headers = []

            # Collect all keys for the header (column names) dynamically, excluding the specified headers
            headers = sorted(set(key for row in record_data for key in row.keys() if key not in excluded_headers))

            total_a_recs = json_response.get('total_a_recs')
            if record_type == 'a' and total_a_recs != 0:
            # Add a special first row with the total A records count
                table_message = f"**A Records ({total_a_recs} total)**\n\n"
            else:
                table_message = f"**{record_type.upper()} Records**\n\n"

            # Create the markdown table for the record type
            table_message += "| " + " | ".join(headers) + " |\n"
            table_message += "| " + " | ".join(["---"] * len(headers)) + " |\n"

            # Add rows to the markdown table, excluding the excluded headers
            for row in record_data:
                row_values = [str(row.get(header, '')) for header in headers]
                table_message += "| " + " | ".join(row_values) + " |\n"

            return table_message

        # Dictionary to store the data for each DNS record type
        record_type_data = {}

        # Collect the data for each record type (A, NS, MX, CNAME, etc.)
        collect_data(json_response, record_type_data)
        # Generate markdown tables for each record type and append to messages
        if record_type_data:
            for record_type, record_data in record_type_data.items():
                if record_type_data.get(record_type):
                    table_message = generate_markdown_table(record_type, record_data, excluded_headers=['country', 'banners'])
                    if table_message:
                        messages.append({'text': table_message.strip()})
                else:
                    messages.append({'text': f"No `{record_type.upper()}` records are found."})

        else:
            messages.append({'text': f"No DNS data found for `{param}`."}) # No records are found at all.

    except requests.exceptions.RequestException as e:
        if response.status_code == 400:
            messages.append({'text': f"Domain `{param}` is invalid."})
        elif response.status_code == 429:
            messages.append({'text': f"Rate limit exceeded."})
        else:    
            # Handle HTTP request errors
            messages.append({'text': f"An HTTP error occurred querying DNSDumpster:\nError: {str(e)}\n{traceback.format_exc()}"})
    except Exception as e:
        # Catch other unexpected errors
        messages.append({'text': f"An error occurred querying DNSDumpster:\nError: {str(e)}\n{traceback.format_exc()}"})
    finally:
        return {'messages': messages}