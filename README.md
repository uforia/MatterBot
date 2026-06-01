# MatterBot

The code on this repository is GPLv3, (c) Arnim Eijkhoudt, 2022-2026.

- Official github repository: https://github.com/uforia/matterbot/
- Please do not approach the developers (including me) for API keys, CTI data, etc.; you need to provide your own :-)
- Pull/feature requests and comments are welcome: please open/post them on GitHub
- If you are looking to deploy MatterBot for commercial purposes, please reach out to me
  via the uforia[@]dhcp[.]net email adress

## Status

Code probably has bugs, but it is officially in a 'works for me' and 'works for others' state ;-)

## Contents

MatterBot consists of two parts, `matterbot` and `matterfeed`, that can be run mostly independently. `matterfeed` aggregates information from various resources (see table below) on a set schedule and posts those in a channel. `matterbot` sits in at least one or more channels, and listens for commands/triggers to spring into action and e.g. collect information for you from various online and local resources via API calls.

Both `matterbot` and `matterfeed` should be run within a `tmux` or `screen` session. The code does not daemonize itself, and there are no plans to implement this currently.

## `matterfeed` Sources

`matterfeed` aggregates **200+ news, advisory, and threat-intel sources** (RSS plus a
handful of API-based feeds) and posts updates to a channel on a schedule. Sources are
grouped into topics you can subscribe to or unsubscribe from individually or in bulk.

**→ [Full source list](docs/FEEDS.md)**

New `matterfeed` modules can be created — a boilerplate example lives in the `modules`
directory.

## `matterbot` Commands

`matterbot` listens for `@command` triggers in its channels and runs the matching
module. It ships **95+ commands** spanning threat-intel reputation/enrichment
(VirusTotal, Shodan, GreyNoise, AlienVault OTX, …), surface search (Onyphe, FOFA,
ZoomEye, Hunter.how, Netlas, …), OSINT/recon (GHunt, Holehe, WiGLE, ChainAbuse, …),
vulnerability management (OpenCVE, EUVD, VulnCheck, VARIoT, …), MITRE tooling
(AttackMatrix, D3FEND, Caldera), and LLM/utility helpers.

**→ [Full command list](docs/COMMANDS.md)**

New `matterbot` modules can be created — a boilerplate example lives in the `commands`
directory.

## Requirements

### Python

- Tested with Python 3.10+, although earlier Python 3 versions might work (test at your own discretion). Most modern distributions should be able to run this.
- Make sure to install the Python requirements (see `requirements.txt`).
- For GraphViz support (e.g. AttackMatrix visual graph generation), you will need to install GraphViz for your distribution/OS. Make sure that it includes **GTS** *(GNU Triangulated Surface)* support.

### Mattermost

- A Mattermost instance, preferably a recent version.
- A 'bot account' on that Mattermost instance. The bot should no longer need an 'admin' account on Mattermost to operate.
- Inviting the bot to the correct channels, both for outputting the results from its feed parsing and so it can listen to commands!

## matterfeed.py

### General information

`matterfeed.py` goes through the `modules` directory and will run all detected modules every (by default) 10 minutes, outputting the results to the specified channels. Every module has its own custom configuration: you'll need to check the individual directories for more information. For example, the WikiJS module requires you to have a WikiJS instance with GraphQL API access, as well as a Microsoft Azure Search instance. You'll need to put the API key etc. in its configuration for it to work properly.

### Getting started

1) Copy `config.defaults.yaml` to `config.yaml` and edit the settings.
2) For every module you want to use, check the respective configuration in `modules/.../`. If you do not want to use a `feed` module, the easiest way to disable it is to move the directory somewhere else (or delete it), so it will not be detected on startup.
3) Start up the `matterfeed.py` and watch the logfile for errors.

### Configuring channel newsfeeds

Optionally, admins and users can create a channel with its own custom newsfeed. After adding the bot to the channel, there are commands to (un)subscribe from/to specific feeds or topics. Every feed module has an `ADMIN_ONLY` setting, which is either set to `True` or `False`. This is a hardcoded value which indicates that the module is user-(un)subscribable or not. Additionally, a global configuration setting in your `config.yaml` determines whether only bot admins or users may (de)activate feeds in a channel.  

Usage is simple:  

- Type `@feeds` to see all available topics and (de)activated feeds;  
- To (un)subscribe from/to specific feed names, use the `@sub`, `@unsub`, `@subscribe`, `@unsubscribe` commands followed by one or more feed names, e.g.: `@sub <feedname1> <feedname2> ... <feednameN>`;
- It is also possible to (de)activate feeds based on topics. Use the same `@sub`, `@unsub`, `@subscribe`, `@unsubscribe` commands but specify a topic, e.g.: `@sub Advisories`.  

## matterbot.py

### General information

`matterbot.py` goes through the `commands` directory and will start listening in every specified channel for every specified bind (command). Every module has its own custom configuration: you'll need to check the individual directories for more information. For example, the ChatGPT module requires you to have an OpenAI account with API access, and you'll need to enter the API key etc. into the configuration for it to work. After starting up the bot, you can use the `@bind`, `@unbind` and `@map` commands to get an overview of, and enable/disable commands in other channels.

### Getting started

1) Copy `config.defaults.yaml` to `config.yaml` and edit the settings.
2) For every module you want to use, check the respective configuration in `commands/.../`. **You must make create your own `settings.py` for every module in the `commands/.../` directory you want to use!** This is necessary so the bot can override the default configuration from `defaults.py`.. If you do not want to use a module, the easiest way to disable it is to move the directory somewhere else (or delete it), so it will not be detected on startup.
3) Start up the `matterbot.py`.

## Configuring Matterbot behavior

When doing threat intelligence investigations, it is crucial to observe Operational Security (OPSEC) best practices. Therefore, by default:

1. MatterBot will not join any channels;

2. MatterBot does not run with or need Mattermost Administrator access;

3. MatterBot will not listen to any commands in a channel it gets added to.

*Note: module configurations (e.g. in `settings.py`) may override this behavior!*

### Configuring channel module listeners

1. After setting up a channel (public or private), manually add the MatterBot to that channel;

2. Use the `@map` command (these triggers may be changed in the `config..yaml`) to list all available modules and whether they are currently enabled for the channel or not;

3. Use `@bind <modulename>` or `@unbind <modulename>` to respectively enable and disable a specific module for a channel, or ...

4. ... use `@bind *` / `@unbind *` to enable/disable all modules.

### OPSEC considerations and best practices

- Some modules will reach out to online internet services! Whether or not this is an OPSEC concern, may depend on your threat model, if you are using paid API access, etc. **It is solely up to you to decide whether or not this is an acceptable risk!** By using MatterBot, you agree not to hold the author(s) responsible/liable for any OPSEC failures or resulting damage;

- Consider using separate Mattermost channels for:
  
  - projects;
  
  - incidents;
  
  - day-to-day discussions;
  
  - 'security clearance' levels;
  
  - etc.

- Use the MatterBot modules binding/unbinding feature (see above) to only enable MatterBot modules that align with your 'risk appetite' for each individual Mattermost channel.

## Writing your own module

- For `matterfeed.py`, it is relatively simple to copy an existing module and alter it to your own needs. Make sure to update the `pathlib` construct to reflect the right module and directory names.

- `matterbot.py` is a fully asynchronous setup, which has both advantages and limitations. The `example` command is a good place to learn more and start developing your own command handler. Pay particular attention to the description in the `commands/example/command.py` file for more information on how to get started and to avoid common pitfalls.

## General known issues and to-do's

- Code cleanups and optimizations
- Better (generalized) logging and error handling

## Acknowledgements

MatterBot would not be possible without the amazing work and/or generous help of others. If I have erroneously failed to list you here, please let me know! In alphabetical order, the people/organisations/companies I would particularly like to thank are:

- Broadcom Symantec: For providing an API key that let me develop integration with Broadcom Symantec Security Cloud
- CERT Polska (CERT.pl): For their awesome MWDB analysis/sandboxing platform and excellent API documentation
- The Dutch Immigration and Naturalisation Service (IND): generous donation of time/code for crt.sh, HaveIBeenPwned and IPinfo
- GTFOBins: The GTFOBins project https://gtfobins.github.io/, in particular *AИDREA* for providing a simple single file download upon request
- LOLBAS: The LOLBAS project https://lolbas-project.github.io/#
- LOLDrivers: The LOLDrivers project https://www.loldrivers.io/
- LOOBINS: The LOOBINS project https://loobins.io/
- LOLRMM: The LOLRMM project https://lolrmm.io/
- Malpedia: Being an amazing community and accepting me into it many years ago https://malpedia.caad.fkie.fraunhofer.de/
- MalwareBazaar: The author(s), for helping me iron out some bugs https://bazaar.abuse.ch
- MISP: For being an absolutely amazing open-source platform for TI exchange https://misp-project.org
- ReversingLabs: For providing an API key to Spectra Analyze and TICloud to develop the integration (particular thank you to D.H.!)
- ThreatFox: The author(s), for helping me iron out some bugs https://threatfox.abuse.ch
- Tria.ge: For providing an API key to build the MatterBot integration;
- Tycho van Marle: for his countless suggestions and contributions to the project
- Unprotect.it: The author(s), for being receptive, kind and open to me including default (download) support for their project https://unprotect.it
- URLhaus: The author(s), for helping me iron out some bugs https://urlhaus.abuse.ch

Additional thanks to AlienVault, Censys, RecordedFuture, Shodan, Tweetfeed, VirusTotal for providing good API documentation, letting me easily write plugins for their services.
