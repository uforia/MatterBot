#!/usr/bin/env python3

from argostranslate import package, translate
import requests
import traceback
from pathlib import Path

# Import settings with fallback logic
def load_settings():
    try:
        from commands.argostrans import defaults as settings
    except ModuleNotFoundError:
        import defaults as settings
        if Path('settings.py').is_file():
            import settings
    else:
        if Path('commands/argostrans/settings.py').is_file():
            try:
                from commands.argostrans import settings
            except ModuleNotFoundError:
                import settings

    return settings

settings = load_settings()

def process(command, channel, username, params, files, conn):

    if not params:
        return {'messages': [{'text': "No parameters provided."}]}

    try:
        messages = []
        allowedFrom = []
        allowedTo = []

        def translationTable():
            try:
                url = settings.PACKAGES

                # Request data from the API
                response = requests.get(url)
                response.raise_for_status()

                json_response = response.json()

                # Create a markdown table for every available language pack in the index from or to the DEFAULT_LAN               
                table = "| " + "Source language " +  "| Destination language " + "| From code " +  "| To code " + "|\n"
                table += "| " + " | ".join(["---"] * 4) + " |\n"
                
                for language in json_response:
                    fromLanCode = language['from_code']
                    fromLanName = language['from_name']
                    toLanCode = language['to_code']
                    toLanName = language['to_name']

                    if fromLanCode or toLanCode == settings.DEFAULT_LAN:
                        table += "| " + f"{fromLanName} " +  f"| {toLanName} " + f"| {fromLanCode} " +  f"| {toLanCode} " + "|\n"
                        if fromLanCode not in allowedFrom:
                            allowedFrom.append(fromLanCode)
                        elif toLanCode not in allowedTo:
                            allowedTo.append(toLanCode)
                    
            except requests.exceptions.RequestException as e:
                # Handle HTTP request errors
                messages.append({'text': f"An HTTP error occurred querying language packages:\nError: {str(e)}\n{traceback.format_exc()}"})
            return table, allowedFrom, allowedTo
        
        allowedFrom = translationTable()[1]
        allowedTo = translationTable()[2]

        sourceLan = params[0]
        if not sourceLan or len(sourceLan) != 2 or sourceLan not in allowedFrom:
            if sourceLan != '-h':
                messages.append({'text': f"`{sourceLan}` is not a valid source language code, choose from:"})
            return messages.append({'text': translationTable()[0]})

        prefLan = params[1]
        content = params[2:]

        def translateString(content, sourceLan, prefLan, destLan=settings.DEFAULT_LAN):

            package.update_package_index()
            updateIndex = package.get_available_packages()

            if len(prefLan) != 2 or prefLan not in allowedFrom:
                if len(prefLan) == 2:
                    messages.append({'text': f"`{prefLan}` is not a valid language code, choose from:"})
                    return messages.append({'text': translationTable()[0]})
                messages.append({'text': f"Defaulting to `{destLan}`"})
                prefLan=destLan
                content = params[1:]
            else:
                destLan=prefLan
                content = params[2:]
            content=content[0]

            # Filter for correct language packages
            try:
                packageSelection = next(filter(lambda x: x.from_code == sourceLan and x.to_code == destLan, updateIndex))
            except:
                messages.append({'text': f"{sourceLan} → {destLan} is not a valid translation pair."})
                return messages.append({'text': translationTable()[0]})
            
            package.install_from_path(packageSelection.download())
            messages.append({'text': f"Attempting to translate {packageSelection}"})
            translation = translate.translate(content, sourceLan, destLan)
            return messages.append({'text': f"Translation\n`{translation}`"})
        
        translateString(content, sourceLan, prefLan)

    except Exception as e:
        # Catch other unexpected errors
        messages.append({'text': f"An error occurred querying Argostranslate:\nError: {str(e)}\n{traceback.format_exc()}"})
    finally:
        return {'messages': messages}