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
| ----------------------------------------------------------- |:--------------:|:----------------:|:-----------------:|
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

New Matterfeed modules can be created. A boilerplate example can be found in the `modules` directory.

### `matterbot` Commands

The Matterbot component listens in a given set of channels (configurable per module) for user-definable commands, executes and returns the results of the module code. The currently supported commands are listed below:

| Name                                    | Type                  | Functionality / Use Case                                                                                                                                                                                       | API Key Required                                                    | Paid Subscription                                                                                                                  |     |
| --------------------------------------- | --------------------- |:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |:-------------------------------------------------------------------:|:----------------------------------------------------------------------------------------------------------------------------------:| --- |
| ASN WHOIS                               | Threat Intel          | Look up Autonomous System Numbers and return the ownership, peering and location information                                                                                                                   | No                                                                  | No                                                                                                                                 |     |
| AttackMatrix                            | Threat Intel          | Query an [AttackMatrix](https://github.com/uforia/AttackMatrix) instance for e.g. MITRE ATT&CK IDs, Actor- and TTP-overlap. Requires Python GraphViz bindings to display the accompanying Graph.               | No, unless the AttackMatrix API is configured to require an API key | No                                                                                                                                 |     |
| Broadcom Symantec Security Cloud (BSSC) | Threat Intel          | Retrieve 'Threat Intel Insight' information for SHA256 file hashes, IPs, reputations, domains and URLs                                                                                                         | Yes                                                                 | Yes                                                                                                                                |     |
| Censys                                  | Threat Intel          | Query Censys for IPs and SHA256 certificate fingerprints. Query results are returned as the original Censys JSON blob.                                                                                         | Yes                                                                 | No: basic functionality<br />Yes: additional features, such as pagination                                                          |     |
| ChatGPT                                 | LLM / GPT queries     | Ask OpenAI's ChatGPT singular questions (no  support for chat history).                                                                                                                                        | Yes                                                                 | Yes                                                                                                                                |     |
| Diceroll                                | Fun                   | Roll any kind of dice combination: #d# format.                                                                                                                                                                 | No                                                                  | No                                                                                                                                 |     |
| Early Warning & Advisory (EWA)          | Threat Intel          | Create Early Warning & Advisory documents using the National Vulnerability Database (NVD) and WikiJS information. Requires pandoc,  pypandoc, LaTeX, a WikiJS instance and a CSS template for final rendering. | No (for NVD)<br />Yes (for WikiJS)                                  | No                                                                                                                                 |     |
| GeoLocation                             | Threat Intel          | Convert latitude/longitude  values into an address.                                                                                                                                                            | No                                                                  | No                                                                                                                                 |     |
| IPWHOIS                                 | Threat Intel          | Look up IP address information: ownership, ASN, geolocation information.                                                                                                                                       | No                                                                  | No                                                                                                                                 |     |
| Malpedia                                | Threat Intel          | Look up malware families, threat actors and MD5/SHA256 malware hashes.                                                                                                                                         | No: basic functionality<br />Yes: malware downloads                 | No                                                                                                                                 |     |
| MalwareBazaar                           | Threat Intel          | Query MalwareBazaar for MD5/SHA1/SHA256 hashes of malware. Will also return include a downloadable malware sample, if available.                                                                               | No                                                                  | No                                                                                                                                 |     |
| MISP                                    | Threat Intel          | Wildcard-searching of a MISP instance for the given search terms. Returns links to the MISP Events where the search terms have been found.                                                                     | Yes                                                                 | No                                                                                                                                 |     |
| RIPE WHOIS                              | Threat Intel          | Look up IP address information: ownership, CIDR and geolocation information.                                                                                                                                   | No                                                                  | No                                                                                                                                 |     |
| Shodan                                  | Threat Intel          | Query Shodan for IP address or host information, as well as performing `count` and `search` queries. Results will include the original Shodan JSON blob as a download.                                         | Yes                                                                 | No: basic functionality<br />Yes: pagination, search queries, etc.                                                                 |     |
| SSLMate                                 | Threat Intel          | Look up SSL/TLS SHA256 hashes in the Certificate Transparency logs. Returns historic data, related hostnames, revocation status and validity times.                                                            | Yes                                                                 | No                                                                                                                                 |     |
| ThreatFox                               | Threat Intel          | Query ThreatFox for MD5/SHA1/SHA256 hashes, IP addresses.                                                                                                                                                      | No                                                                  | No                                                                                                                                 |     |
| TLSGrab                                 | Threat Intel          | Connect to the given IP address + port, and attempt to retrieve the TLS certificate CNs. *Note: this is an OPSEC risk, because the bot will actively attempt to connect to the host/port!*                     | No                                                                  | No                                                                                                                                 |     |
| Unprotect.it                            | Threat Intel          | Search the Unprotect.it project for information on TTPs, code snippets and detection rules. Returns code snippets and detection rules as a download, if available.                                             | No                                                                  | No                                                                                                                                 |     |
| URLhaus                                 | Threat Intel          | Look up reputation info on URLhaus for URLs and MD5 / SHA1 / SHA256 URL hashes.                                                                                                                                | No                                                                  | No                                                                                                                                 |     |
| VirusTotal                              | Threat Intel          | Search VirusTotal for IP addresses, MD5/SHA1/SHA256 hashes, URLs and domains. Returned results will include maliciousness, TTP sets, malware family names, etc., if available.                                 | Yes                                                                 | No: basic functionality<br />Yes: paid VT features, throttling limit removal, etc.                                                 |     |
| WikiJS                                  | Information Retrieval | Search through WikiJS pages' contents for the given search terms. Returns links to the pages where the contents were found.                                                                                    | Yes                                                                 | Yes: currently requires a Microsoft Azure Search instance  that indexes the WikiJS instance (*Note: this is a WikiJS limitation!*) |     |

New Matterbot modules can be created. A boilerplate example can be found in the `commands` directory.

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
