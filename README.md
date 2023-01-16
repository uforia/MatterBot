# MatterBot

Code is GPLv3, (c) Arnim Eijkhoudt, KPN, 2022/2023.

Official github repository: https://github.com/uforia/matterbot/.
Pull/feature requests and comments are welcome.

## Status

Initial release. Code is probably still buggy, but at least it's in a 'works for me' state ;-)

## Contents

MatterBot consists of two parts that can be run independently: matterbot and matterfeed. Both parts should be run within tmux or screen; the code itself is not daemonized (this may happen at some point in the future).

### Currently supported by `matterfeed`

- Bruce Schneier's blog (RSS)
- CISA.gov Security Announcements (RSS)
- Cqure blog (RSS)
- DarkReading news (RSS)
- GBHackers news (RSS)
- Kitploit tools (RSS)
- Knowbe4 news (RSS)
- KrebsOnSecurity blog (RSS)
- MajorLeagueHacking news (RSS)
- Microsoft Vulnerability reports (RSS)
- NCSC NL (Netherlands) Vulnerability reports (RSS)
- NCSC UK Vulnerability reports (RSS)
- SecureList news (RSS)
- TheHackerNews news (RSS)
- Threatpost news (RSS)
- Twitter users' posts, as followed by the account configured
- Velociraptor news/updates (RSS)
- WeLiveSecurity news (RSS)
- WikiJS (Monitoring changes to the popular Wiki software)

### Currently supported by `matterbot`

- Censys: search for IPs, SHA256 certificate fingerprints (*)
- ChatGPT: ask OpenAI's ChatGPT individual questions (no history) (*)
- Diceroll: rolling dice
- Example: module with instructions for developing your own
- IPWHOIS: query IP WHOIS for IP address information
- Malpedia: search for MD5/SHA256 malware hashes, malware families or threat actors (*)
- MalwareBazaar: search for MD5/SHA1/SHA256 hashes
- MISP: query your MISP instance for any IoC type (*)
- RIPE WHOIS: query RIPE for WHOIS information
- Shodan: search for IP or hostname information, and performing `count` and `search` queries (*)
- ThreatFox: search for MD5/SHA1/SHA256 hashes, IP addresses
- URLHaus: search for MD5/SHA1/SHA256 hashes, URLs
- VirusTotal: search for IPs, MD5/SHA1/SHA256 hashes, URLs, domains (*)
- WikiJS: search your WikiJS instance for information (*)

(*): Module requires (paid) API access for partial or full functionality

## Requirements

### Python

- Tested with Python 3.10+, although earlier Python 3 versions might work (test at your own discretion). Most modern distributions should be able to run this.
- Make sure to install the Python requirements (see `requirements.txt`).

### Mattermost

- A Mattermost instance.
- A 'bot account' on that Mattermost instance.
- Remember to invite the bot to the correct channels, both for outputting the results from its feed parsing and so it can listen to commands!

## matterfeed.py

### General information

`matterfeed.py` goes through the `modules` directory and will run all detected modules every 5 minutes, outputting the results to the specified channels. Every module has its own custom configuration: you'll need to check the individual directories for more information. For example, the Twitter module requires you to have a Twitter account with API/bot access, and you'll need to put the API key etc. in the configuration for it to work.

### Getting started

1) Copy `config.defaults.yaml` to `config.yaml` and edit the settings.
2) For every module you want to use, check the respective configuration in `modules/.../`. Create a `settings.py` and use that to override the configuration from `defaults.py`. If you do not want to use a module, the easiest way to disable it is to rename the `feed.py` file to something else, so it will not be detected on startup.
3) Start up the `matterfeed.py` and watch the logfile for errors.

## matterbot.py

### General information

`matterbot.py` goes through the `commands` directory and will start listening in every specified channel for every specified bind (command). Every module has its own custom configuration: you'll need to check the individual directories for more information. For example, the ChatGPT module requires you to have an OpenAI account with API access, and you'll need to put the API key etc. in the configuration for it to work.

### Getting started

1) Copy `config.defaults.yaml` to `config.yaml` and edit the settings.
2) For every module you want to use, check the respective configuration in `commands/.../`. Create a `settings.py` and use that to override the configuration from `defaults.py`. If you do not want to use a module, the easiest way to disable it is to rename the `command.py` file to something else, so it will not be detected on startup.
3) Start up the `matterbot.py`.

## Writing your own module

- For `matterfeed.py`, it is relatively simple to copy an existing module and alter it to your own needs. Make sure to update the `pathlib` construct to reflect the right module and directory names.

- `matterbot.py` is a fully asynchronous setup, which has both advantages and limitations. The `example` command is a good place to learn more and start developing your own command handler. Pay particular attention to the description in the `commands/example/command.py` file for more information on how to get started and to avoid common pitfalls.

## General known issues and to-do's

- Code cleanups and optimizations
- Better (generalized) logging and error handling
