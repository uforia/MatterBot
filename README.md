# MatterBot

Code is GPLv3, (c) Arnim Eijkhoudt, KPN, 2022/2023.

Official github repository: https://github.com/uforia/matterbot/.
Pull/feature requests and comments are welcome.

## Status

Code probably has bugs, but at least it's in a 'works for me' state ;-)

## Contents

MatterBot consists of two parts that can be run independently: matterbot and matterfeed. Both parts should be run within tmux or screen; the code itself is not daemonized (this may happen at some point in the future).

### `matterfeed` Sources

Matterfeed reports news updates on a set schedule. The currently supported sources are listed in the table below:

| Name                                                        | Type           | API Key Required | Paid Subscription |
| ----------------------------------------------------------- | -------------- | ---------------- | ----------------- |
| Bruce Schneier's Blog                                       | RSS            | No               | No                |
| CISA.gov Security Announcements                             | RSS            | No               | No                |
| Cqure Blog                                                  | RSS            | No               | No                |
| DarkReading News                                            | RSS            | No               | No                |
| GBHackers News                                              | RSS            | No               | No                |
| Kitploit Tool Updates                                       | RSS            | No               | No                |
| KnowBe4 News                                                | RSS            | No               | No                |
| KrebsOnSecurity Blog                                        | RSS            | No               | No                |
| MajorLeagueHacking News                                     | RSS            | No               | No                |
| Microsoft Vulnerability Reports                             | RSS            | No               | No                |
| NCSC Netherlands Advisories                                 | RSS            | No               | No                |
| NCSC United Kingdom Advisories                              | RSS            | No               | No                |
| SecureList News                                             | RSS            | No               | No                |
| TheHackerNews News                                          | RSS            | No               | No                |
| Threatpost News                                             | RSS            | No               | No                |
| Twitter Posts (from all users the account is subscribed to) | Twitter        | Yes              | Yes               |
| Velociraptor News/Updates                                   | RSS            | No               | No                |
| WeLiveSecurity News                                         | RSS            | No               | No                |
| WikiJS Page Updates                                         | WikiJS GraphQL | Yes              | No                |

New Matterfeed modules can be created. A boilerplate example can be found in the modules directory.

### `matterbot` Commands

The Matterbot component listens in a given set of channels (configurable per module) for user-definable commands, executes and returns the results of the module code. The currently supported commands are listed below:

| Name      | Type         | Functionality / Use Case | API Key Required | Paid Subscription |     |
| --------- | ------------ | ------------------------ | ---------------- | ----------------- | --- |
| ASN WHOIS | Threat Intel |                          |                  |                   |     |



- ASN WHOIS: look up Autonomous System Numbers and return the ownership, peering and location information
- AttackMatrix: query an [AttackMatrix](https://github.com/uforia/AttackMatrix) instance for MITRE ATT&CK IDs, Actor- and TTP-overlap
- Broadcom Symantec Security Cloud: retrieve 'Threat Intel Insight' information for SHA256 file hashes, IPs, domains and URLs (*)
- Censys: search for IPs, SHA256 certificate fingerprints (*)
- ChatGPT: ask OpenAI's ChatGPT individual questions (no history) (*)
- Diceroll: rolling dice
- EWA: generate Early Warning / Advisory announcements using NVD and WikiJS (**)
- Example: module with instructions for developing your own
- GeoLocation: transform latitude/longitude into an address, if possible
- IPWHOIS: query IP WHOIS for IP address information
- Malpedia: search for MD5/SHA256 malware hashes, malware families or threat actors (*)
- MalwareBazaar: search for MD5/SHA1/SHA256 hashes
- MISP: query your MISP instance for any IoC type (*)
- RIPE WHOIS: query RIPE for WHOIS information
- Shodan: search for IP or hostname information, run `count` and `search` queries (*)
- SSLMate: search for SHA256 hashes in Certificate Transparency logs (*)
- ThreatFox: search for MD5/SHA1/SHA256 hashes, IP addresses
- TLSGrab: connect to the given IP address(es) and attempt to retrieve the TLS certificate CNs, if available
- Unprotect.it: search through and return information on TTPs, code snippets and detection rules
- URLHaus: search for MD5/SHA1/SHA256 hashes, URLs
- VirusTotal: search for IPs, MD5/SHA1/SHA256 hashes, URLs, domains (*)
- WikiJS: search your WikiJS instance for information (*)

(*): Module requires (paid) API access for partial or full functionality!  
(**): The EWA module requires a complete Pandoc, pypandoc and (La)TeX setup to function, as well as your own CSS rendering template

## Requirements

### Python

- Tested with Python 3.10+, although earlier Python 3 versions might work (test at your own discretion). Most modern distributions should be able to run this.
- Make sure to install the Python requirements (see `requirements.txt`).
- For GraphViz support (e.g. AttackMatrix API calls), you will need to install GraphViz for your distribution/OS. Make sure that it includes **GTS** *(GNU Triangulated Surface)* support.

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
