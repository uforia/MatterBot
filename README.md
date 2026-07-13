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

## AI Analyst (optional)

MatterBot can run an optional conversational AI analyst. You talk to it in a
Mattermost thread, in plain language, and it uses MatterBot's own command modules
as tools to investigate the case with you:

> **you:** `@ai we're seeing beacons to 8.8.8[.]8 and a dropped file d41d8cd98f00b204e9800998ecf8427e, thoughts?`
>
> **bot:** *The hash is a known Emotet loader (MalwareBazaar, ThreatFox). The IP is
> clean across AbuseIPDB and passive DNS — it looks like staging infrastructure
> rather than the C2. The sample resolves to `bad.example.com`; want me to pull the
> linked infrastructure?*
>
> **you:** `yes`

The thread is the case. Reply in it to continue; start a new `@ai` message in the
channel to open a fresh one. The AI reads **only its own thread** — never the rest
of the channel.

### Requirements

- **An OpenAI-compatible endpoint serving a model with native function-calling
  support.** This is a hard requirement: a model that cannot emit tool calls will
  not work, and there is no text-protocol fallback. Ollama (with a tool-capable
  model), vLLM, LiteLLM and the cloud APIs all work.
- At least one command module with `AITOOL = True`.
- No new Python dependency — the client is a thin `requests` wrapper.

### Enabling it

Add (or uncomment) the `AI:` block in your `config.yaml` — see
`config.defaults.yaml` for the fully annotated version:

```yaml
AI:
  enabled: True
  base_url: "http://localhost:11434/v1"
  model: "<a function-calling-capable model>"
  api_key: "ollama"
  bind: "@ai"
  evidence: "compact"
```

**With no `AI:` block, or `enabled: False`, the feature is completely inert:** the
`@ai` bind is never registered and MatterBot behaves exactly as it did before.

### What the AI can and cannot do

The safety rules are enforced **in code, at the tool executor** — not asked for in
the prompt. Threat-intel results contain attacker-influenceable text (WHOIS fields,
filenames, page content, submitted comments), so indirect prompt injection is a real
risk, and the answer to it is that a hijacked model still cannot do anything it was
not already allowed to do:

- **It can only look up indicators you named.** If it discovers a new indicator worth
  pivoting to, it *proposes* it and waits — say "yes" and it proceeds. It cannot query
  an unapproved indicator no matter what any prompt, or any tool result, tells it.
  Note that a bare "yes" approves *every* indicator the AI proposed that turn, so read
  what it proposed before you approve — a pivot is still only ever a read-only,
  ACL-checked, rate-capped lookup, but approve the ones you meant to.
- **It cannot bypass your ACLs.** A module you may not use, the AI may not use on your
  behalf (`isallowed_module`).
- **It cannot hand a module the wrong kind of indicator** — the module's `ACCEPTS`
  declaration is checked first.
- **It has no write or destructive tools.** v1 is read-only lookups only.
- **It is rate-capped** per turn and per case, bounding runaway loops and paid-API spend.
- **It never sees your API keys.** Module output is redacted (`sanitize_tool_output`)
  before it reaches the model or the channel — including on the success path, because
  the AI is the first feature that sends module output **off your host** to an LLM
  endpoint.

Every tool call the AI makes is logged server-side, and so is every call it was
**denied** — with the user, channel, module, indicator and reason.

### Choosing which modules the AI can use

Two independent switches, and a module needs **both**:

1. **Developer opt-in**, in a module's `defaults.py` (or your `settings.py` override):

   ```python
   ACCEPTS = ['ip', 'ipv6']   # required: the indicator types this module handles
   AITOOL = True              # this module is safe to expose to an AI
   ```

2. **Operator opt-in**, in the `AI:` config block:

   ```yaml
   AI:
     modules: ["abuseipdb", "circlpdns", "crtsh"]  # empty = every AITOOL module
     blocked_modules: ["threatbook"]               # withhold a paid-quota module
   ```

These lists can only ever **restrict**: they cannot expose a module that has not set
`AITOOL`, and they cannot override a user's channel ACLs.

MatterBot ships with a curated starter set opted in — `abuseipdb`, `circlpdns`,
`crtsh`, `ipinfo`, `malwarebazaar`, `threatfox` and `urlhaus` — which between them
cover every indicator type. Everything else is off by default, so paid-quota and
free-text modules are never silently reachable by a model.

### Evidence modes

- `compact` (default): an analyst-voice narrative plus a one-line
  `Queried: threatfox(8.8.8.8) → ok` sources footer.
- `full`: the narrative, then the raw module tables as follow-up posts — the same
  output an `@`-command gives you, capped at `max_evidence_chars` per tool.

Switch per-thread with `@ai full …` or `@ai brief …`; the choice sticks for that case.
Raw evidence is tagged and is *not* replayed into the model's context on later turns,
so turning it on does not inflate token cost as the case grows.

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
