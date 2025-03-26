#!/usr/bin/env python3

import json
import requests
import traceback
from pathlib import Path

# Import settings with fallback logic
def load_settings():
    try:
        from commands.haveibeenpwned import defaults as settings
    except ModuleNotFoundError:
        import defaults as settings
        if Path('settings.py').is_file():
            import settings
    else:
        if Path('commands/haveibeenpwned/settings.py').is_file():
            try:
                from commands.haveibeenpwned import settings
            except ModuleNotFoundError:
                import settings

    return settings

settings = load_settings()


def process(command, channel, username, params, files, conn):

    if not params:
        return {'messages': [{'text': "No parameters provided. Type !help @hibp to see what to do"}]}

    param_searchtype = params[0]
    param_searchvalue = params[1]

    api_url_map = {
        "email": settings.APIURL['hibp_email']['url'],
        "domain": settings.APIURL['hibp_domain']['url'],
        "breach": settings.APIURL['hibp_breach']['url'],
    }

    # Check if param_searchtype is valid
    if param_searchtype not in api_url_map:
        return {'messages': [{'text': "No type selected or invalid type. Type !help @hibp to see what to do"}]}

    # Construct API URL
    api_url = f"{api_url_map[param_searchtype]}{param_searchvalue}"

    headers = {
        'Accept-Encoding': settings.CONTENTTYPE,
        'Content-Type': settings.CONTENTTYPE,
        'User-Agent': 'MatterBot integration for HaveIBeenPwned v0.1',
        'hibp-api-key': settings.APIURL['hibp']['key'],
    }

    try:
        messages = []

        # Request data from the API
        response = requests.get(api_url, headers=headers)

        response.raise_for_status()  # Ensure we raise an error for bad status codes

        json_response = response.json()

        # Parse and process the data
        unique_common_names = set()

        message = ""

        if param_searchtype == "email" or param_searchtype == "domain" :

            message += "| Breach Name         |\n"
            message += "|---------------------|\n"

            for entry in json_response:

                if param_searchtype == "email":

                    breach_name = entry.get('Name', 'Unknown Breach Name')

                    # Append formatted information to the message
                    message += f"| {breach_name}         |\n"

                elif param_searchtype == "domain":

                   #TODO
                    message += f"COMING SOON"


        elif param_searchtype == "breach":

            # Extract information from the JSON
            # Extract information from the JSON
            breach_name = json_response.get('Name', 'Unknown Breach Name')
            breach_title = json_response.get('Title', 'Unknown Title')
            breach_domain = json_response.get('Domain', 'Unknown Domain')
            breach_date = json_response.get('BreachDate', 'Unknown Date')
            added_date = json_response.get('AddedDate', 'Unknown Added Date')
            modified_date = json_response.get('ModifiedDate', 'Unknown Modified Date')
            breach_pwn_count = json_response.get('PwnCount', 0)
            breach_description = json_response.get('Description', 'No description available.')
            breach_logo = json_response.get('LogoPath', '')
            breach_data_classes = ', '.join(json_response.get('DataClasses', []))

            # Extract boolean values
            is_verified = json_response.get('IsVerified', False)
            is_fabricated = json_response.get('IsFabricated', False)
            is_sensitive = json_response.get('IsSensitive', False)
            is_retired = json_response.get('IsRetired', False)
            is_spam_list = json_response.get('IsSpamList', False)
            is_malware = json_response.get('IsMalware', False)
            is_subscription_free = json_response.get('IsSubscriptionFree', False)

            # Create the Markdown formatted table
            message += (
                "| Attribute                | Value                                   |\n"
                "|--------------------------|-----------------------------------------|\n"
                f"| Breach Name              | {breach_name}                          |\n"
                f"| Title                    | {breach_title}                         |\n"
                f"| Domain                   | {breach_domain}                        |\n"
                f"| Breach Date              | {breach_date}                          |\n"
                f"| Added Date               | {added_date}                           |\n"
                f"| Modified Date            | {modified_date}                        |\n"
                f"| Total Accounts Compromised| {breach_pwn_count}                     |\n"
                f"| Description              | {breach_description}                   |\n"
                f"| Logo                     | {breach_logo}                          |\n"
                f"| Data Classes             | {breach_data_classes}                  |\n"
                f"| Is Verified              | {is_verified}                          |\n"
                f"| Is Fabricated            | {is_fabricated}                        |\n"
                f"| Is Sensitive             | {is_sensitive}                         |\n"
                f"| Is Retired               | {is_retired}                           |\n"
                f"| Is on Spam List          | {is_spam_list}                         |\n"
                f"| Is Malware               | {is_malware}                           |\n"
                f"| Is Subscription Free     | {is_subscription_free}                |"
            )

        if message:
            messages.append({'text': message.strip()})
        else:
            messages.append({'text': f"No breach data found for `{param_searchvalue}`."})

    except requests.exceptions.RequestException as e:
        # Handle HTTP request errors
        messages.append({'text': 'An HTTP error occurred:\nError: ' + (str(e),traceback.format_exc())})
    except Exception as e:
        # Catch other unexpected errors
        messages.append({'text': 'An error occurred in HIBP:\nError: ' + (str(e),traceback.format_exc())})
    finally:
        return {'messages': messages}
