#!/usr/bin/env python3

import json
import requests
import traceback
from pathlib import Path

# Import settings with fallback logic
def load_settings():
    try:
        from commands.ipinfo import defaults as settings
    except ModuleNotFoundError:
        import defaults as settings
        if Path('settings.py').is_file():
            import settings
    else:
        if Path('commands/ipinfo/settings.py').is_file():
            try:
                from commands.ipinfo import settings
            except ModuleNotFoundError:
                import settings

    return settings

settings = load_settings()


def process(command, channel, username, params, files, conn):

    if not params:

        return {'messages': [{'text': "No parameters provided."}]}
    
    param = params[0]
    
    try:
        messages = []

        # API URL for fetching data
        api_url = f"{settings.APIURL['ipinfo']['url']}{param}?token={settings.APIURL['ipinfo']['key']}"

        # Request headers
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'User-Agent': 'MatterBot integration for ipinfo v0.1',
        }

        # Request data from the API
        response = requests.get(api_url)

        #  Ensure we raise an error for bad status codes
        response.raise_for_status()

        # Assign response to variable
        json_response = response.json()

        # Parse and process the data
        unique_common_names = set()
        
        message = ""

        ip_address = json_response.get('ip', 'Unknown IP')
        city = json_response.get('city', 'Unknown City')
        region = json_response.get('region', 'Unknown Region')
        country = json_response.get('country', 'Unknown Country').lower()
        location = json_response.get('loc', 'Unknown Location')
        org = json_response.get('org', 'Unknown Organization')
        postal_code = json_response.get('postal', 'Unknown Postal Code')
        timezone = json_response.get('timezone', 'Unknown Timezone')

        # Create a Markdown formatted table with the information
        message += f"Here are the IPInfo results for: {param}\n\n\n"
        message += (
            "| IP Address      | City            | Region          | Country         | GPS Coordinates | Organization    | Postal Code     | Timezone        |\n"
            "|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|\n"
            f"| `{ip_address}`    | `{city}`          | `{region}`        | :flag-{country}: | `{location}`      | `{org}`           | `{postal_code}`   | `{timezone}`     |"
        )
        if message:
            messages.append({'text': message.strip()})
        else:
            messages.append({'text': f"No IPinfo data found for `{param}`."})

    except requests.exceptions.RequestException as e:
        # Handle HTTP request errors
        messages.append({'text': 'An HTTP error occurred querying ipinfo:\nError: ' + (str(e),traceback.format_exc())})
    except Exception as e:
        # Catch other unexpected errors
        messages.append({'text': 'An error occurred querying ipinfo:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}