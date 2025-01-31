import json
import requests
from pathlib import Path
import re
import traceback

# Import settings with fallback logic
def load_settings():
    try:
        from commands.crtsh import defaults as settings
    except ModuleNotFoundError:
        import defaults as settings
        if Path('settings.py').is_file():
            import settings
    else:
        if Path('commands/crtsh/settings.py').is_file():
            try:
                from commands.crtsh import settings
            except ModuleNotFoundError:
                import settings

    return settings

settings = load_settings()

# Function to validate a domain name using regex
def is_valid_domain(domain):
    # Regular expression to validate a domain name
    domain_regex = r"^(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+(?:[A-Za-z]{2,})$"
    return bool(re.match(domain_regex, domain))


def process(command, channel, username, params, files, conn):

    messages = []

    param = params[0] if params else None

    # Validate the input parameter as a valid IP address
    if not is_valid_domain(param):
        messages = ""
    
    
    try:
        # API URL for fetching data
        headers = {
            'Content-Type': settings.CONTENTTYPE,
            'User-Agent': 'MatterBot integration for ASNWHOIS v0.1'
        }
        api_url = f"{settings.APIURL['crtsh']['url']}{param}"

        # Request data from the API
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Ensure we raise an error for bad status codes
        json_response = response.json()

        table_message = ""
        unique_common_names = set()

        # Create the header of the table
        table_message += f"Here are the crt.sh results for: {param}\n\n"
        table_message += "| Issuer Name     | Common Name     | Entry Time      | Validity        |\n"
        table_message += "|-----------------|-----------------|-----------------|-----------------|\n"
        table_message += "|||| |\n"

        # Iterate through entries in the JSON response
        for entry in json_response:

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

        messages.append({'text': table_message.strip()})

    except Exception as e:
        # Append error message to the messages list
        messages.append({'text': 'An error occurred in GTFOBins:\nError: ' + (str(e),traceback.format_exc())})

    finally:
        # Return the messages list
        return {'messages': messages}
