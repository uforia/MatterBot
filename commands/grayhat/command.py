#!/usr/bin/env python3

import io
import pandas as pd
import requests
import traceback
from datetime import datetime

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

def process(command, channel, username, params, files, conn,):
    if not params:
        return {'messages': [{'text': "No parameters provided."}]}

    param = params[0:]

    try:
        messages = []
        api_url = f"{settings.APIURL['grayhat']['url']}files?keywords={' '.join(param)}"

        # Request headers
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'Authorization': f"Bearer {settings.APIURL['grayhat']['key']}",
            'User-Agent': 'MatterBot integration for grayhat v1.0',
        }

        # Request data from the API
        response = requests.get(api_url, headers=headers)
        # Ensure we raise an error for bad status codes
        response.raise_for_status()
        # Assign response to variable
        json_response = response.json()

        def output_to_csv(data): # Generate csv for detailed results
            uploads = []
            fname = f'grayhat_{datetime.now().strftime("%m%d%Y_%H%M%S")}.csv'
            df = pd.DataFrame(data)
            df_sorted = df.sort_values(by='lastModified')
            output = io.StringIO()
            df_sorted.to_csv(output, index=False)
            csv_bytes = output.getvalue().encode('utf-8')
            upload = {
                'filename': fname,
                'bytes': csv_bytes
            }
            uploads.append(upload)
            return uploads
        
        def convert_to_gmt(timestamp):
            if isinstance(timestamp, int) or (isinstance(timestamp, str) and timestamp.isdigit()):
                dt = datetime.fromtimestamp(int(timestamp))
                return dt.strftime('%Y-%m-%d %H:%M:%S GMT') # Convert posix timestamp to human readable
            return ''

        def collect_file_data(data):
            records = []
            buckets = set()
            for item in data:
                if isinstance(item, dict):
                    record = {
                        'bucket': item.get('bucket'),
                        'fullPath': item.get('fullPath'),
                        'type': item.get('type'),
                        'size': item.get('size'),
                        'lastModified': convert_to_gmt(item.get('lastModified'))
                    }
                    if record['bucket'] not in buckets:
                        records.append(record)
                        buckets.add(record['bucket'])
            return records

        def generate_markdown_table(data):             
            if not data:
                return "No records found.\n"
            
            table = f"**Showing {len(records)} bucket(s).**\n"
            table += "*It is possible that there is more than 1 file in a bucket, check csv for details.*\n\n"

            headers = ['Bucket', 'Filename', 'Type', 'Size (b)', 'Last Modified (UTC)']
            table += "| " + " | ".join(headers) + " |\n"
            table += "| " + " | ".join([":-"] * len(headers)) + " |\n"

            keys = ['bucket', 'fullPath', 'type', 'size', 'lastModified']
            data_sorted = sorted(data, key=lambda row: row.get('lastModified', ''), reverse=True)
            while len(table) < 10000: # TODO Change to options.Mattermost['msglength'] - X charlength or change to variable msg split with added header
                for row in data_sorted:
                    values = [str(row.get(key, '')) for key in keys]
                    table += "| " + " | ".join(values) + " |\n"
            return table
        
        records = collect_file_data(json_response['files'])
        if records:
            table_msg = generate_markdown_table(records)

            messages.append({'text': table_msg.strip()})
            messages.append({
                'text': 'Grayhatwarfare CSV output', 
                'uploads': output_to_csv(json_response['files'])
                    })
        else:
            messages.append({'text': "No public records found."})

    except requests.exceptions.RequestException as e:
        if response.status_code == 400:
            messages.append({'text': f"Input `{param}` is invalid."})
        elif response.status_code == 429:
            messages.append({'text': f"Rate limit exceeded."})
        else:    
            # Handle HTTP request errors
            messages.append({'text': f"An HTTP error occurred querying grayhat:\n\n{response.status_code} Error: {str(e)} \n{traceback.format_exc()}"})
    except Exception as e:
        # Catch other unexpected errors
        messages.append({'text': f"An error occurred querying grayhat:\n\nError: {str(e)}\n{traceback.format_exc()}"})
    finally:
        return {'messages': messages}
