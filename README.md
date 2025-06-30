# MatterBot

Code is GPLv3, (c) Arnim Eijkhoudt, 2022-2025.

- Official github repository: https://github.com/uforia/MatterBot/
- Pull/feature requests and comments are welcome: please open/post them on GitHub
- If you are looking to deploy MatterBot for commercial purposes, please reach out to me
  via the uforia[@]dhcp[.]net email adress

## Status

Code probably has bugs, but it is officially in a 'works for me' and 'works for others' state ;-)

## Contents

MatterBot consists of two parts that can be run independently: `matterbot` and `matterfeed`. Both parts can be run independently. `matterfeed` aggregates information from various resources (see table below) on a set schedule and posts those in a channel. `matterbot` sits in at least one or more channels, and listens for commands/triggers to spring into action and e.g. collect information for you from various online and local resources via API calls.

Both `matterbot` and `matterfeed` should be run within a `tmux` or `screen` session. The code does not daemonize itself, and there are no plans to implement this currently.

### `matterfeed` Sources

Matterfeed reports news updates on a set schedule. The currently supported sources are listed in the table below:

| Name                                                                                             | Type           | API Key Required | Paid Subscription |
| ------------------------------------------------------------------------------------------------ |:--------------:|:----------------:|:-----------------:|
| 0dayfans Security News                                                                           | RSS            | No               | No                |
| Any.run Cybersecurity Blog                                                                       | RSS            | No               | No                |
| Aqua Security Blog                                                                               | RSS            | No               | No                |
| Arctic Wolf Security Blog                                                                        | RSS            | No               | No                |
| Australian Cyber Security Centre                                                                 | RSS            | No               | No                |
| Bad Sector Labs Newsletter                                                                       | RSS            | No               | No                |
| Barracuda Threat Intelligence                                                                    | RSS            | No               | No                |
| Binary Defense                                                                                   | RSS            | No               | No                |
| Bishop Fox Offensive Security                                                                    | RSS            | No               | No                |
| Bleepingcomputer News                                                                            | RSS            | No               | No                |
| Broadcom Symantec                                                                                | RSS            | No               | No                |
| Bruce Schneier's Blog                                                                            | RSS            | No               | No                |
| Canadian Centre for Cyber Security                                                               | RSS            | No               | No                |
| CERT Bundesrepublik Deutschland                                                                  | RSS            | No               | No                |
| CERT Česká Republika                                                                             | RSS            | No               | No                |
| CERT Eesti Vabariik                                                                              | RSS            | No               | No                |
| CERT European Union                                                                              | RSS            | No               | No                |
| CERT Instituto Nacional de Ciberseguridad                                                        | RSS            | No               | No                |
| CERT Latvijas Republika                                                                          | RSS            | No               | No                |
| CERT Repubblica Italiana                                                                         | RSS            | No               | No                |
| CERT Republik Österreich                                                                         | RSS            | No               | No                |
| CERT Republika Slovenija                                                                         | RSS            | No               | No                |
| CERT République Française                                                                        | RSS            | No               | No                |
| CERT Rzeczpospolita Polska                                                                       | RSS            | No               | No                |
| CERT Türkiye Cumhuriyeti (USOM)                                                                  | RSS            | No               | No                |
| CERT VDE Industrial Advisories                                                                   | RSS            | No               | No                |
| CERT Репу̀блика Бълга̀рия (BG)                                                                     | RSS            | No               | No                |
| CERT Україна (UA)                                                                                | RSS            | No               | No                |
| CERT 中華人民共和國香港特別行政區 (HK)                                                              | RSS            | No               | No                |
| Checkmarx Application Security Blog                                                              | RSS            | No               | No                |
| Checkpoint (Email) Security Research                                                             | RSS            | No               | No                |
| Cisco Security Advisories                                                                        | RSS            | No               | No                |
| CiscoTalos Threat Intelligence                                                                   | RSS            | No               | No                |
| CISecurity                                                                                       | RSS            | No               | No                |
| Cqure Blog                                                                                       | RSS            | No               | No                |
| CSHub (configurable list of CSHub feeds)                                                         | RSS            | No               | No                |
| Cyble Threat Intelligence                                                                        | RSS            | No               | No                |
| DarkNet Blog                                                                                     | RSS            | No               | No                |
| Darkowl Darkweb Intelligence                                                                     | RSS            | No               | No                |
| Darkrelay Offensive Security Blog                                                                | RSS            | No               | No                |
| DataBreaches.Net News                                                                            | RSS            | No               | No                |
| DataBreachToday News                                                                             | RSS            | No               | No                |
| Datadog Security Labs                                                                            | RSS            | No               | No                |
| Deepinstinct Threat Intelligence                                                                 | RSS            | No               | No                |
| DeiC Sikkerhed/DKCERT                                                                            | RSS            | No               | No                |
| DIVD CSIRT                                                                                       | RSS            | No               | No                |
| Dragos OT Security                                                                               | RSS            | No               | No                |
| Eclecticiq Intelligence Research                                                                 | RSS            | No               | No                |
| Eclypsium Threat Research                                                                        | RSS            | No               | No                |
| Elastic Security Labs                                                                            | RSS            | No               | No                |
| F5 Labs Threat Intelligence                                                                      | RSS            | No               | No                |
| FalconForce                                                                                      | RSS            | No               | No                |
| FieldEffect Threat Intelligence                                                                  | RSS            | No               | No                |
| Fortinet PSIRT/Threat Research Blogs                                                             | RSS            | No               | No                |
| GBHackers News                                                                                   | RSS            | No               | No                |
| Google Cloud Threat Intelligence                                                                 | RSS            | No               | No                |
| GreyNoise Threat Intelligence                                                                    | RSS            | No               | No                |
| Group-IB Blog                                                                                    | RSS            | No               | No                |
| Hacktron AI Threat Research                                                                      | RSS            | No               | No                |
| Harfanglab Threat Intelligence                                                                   | RSS            | No               | No                |
| Helpnet Security                                                                                 | RSS            | No               | No                |
| Horizon3 Threat Research                                                                         | RSS            | No               | No                |
| Hudson Rock Infostealers                                                                         | RSS            | No               | No                |
| Huntress Threat Intelligence                                                                     | RSS            | No               | No                |
| IBM X-Force Threat Reports                                                                       | RSS            | No               | No                |
| Internet Crime Complaint Center Industry Alerts                                                  | RSS            | No               | No                |
| Internet Crime Complaint Center Press Releases                                                   | RSS            | No               | No                |
| Imperva Security Blog                                                                            | RSS            | No               | No                |
| Jamf Apple Security Research                                                                     | RSS            | No               | No                |
| JPCERT/CC Warnings & Emergency Bulletins                                                         | RSS            | No               | No                |
| Juniper Network Blogs                                                                            | RSS            | No               | No                |
| Kaspersky SecureList News                                                                        | RSS            | No               | No                |
| Kevin Beaumont@Medium (DoublePulsar)                                                             | RSS            | No               | No                |
| Kitploit Tool Updates                                                                            | RSS            | No               | No                |
| KnowBe4 News                                                                                     | RSS            | No               | No                |
| KQLQuery Blog                                                                                    | RSS            | No               | No                |
| KrebsOnSecurity Blog                                                                             | RSS            | No               | No                |
| Kyberturvallisuuskeskuksen Suomi (NCSC-FI)                                                       | RSS            | No               | No                |
| Lumen Black Lotus Labs                                                                           | RSS            | No               | No                |
| MajorLeagueHacking News                                                                          | RSS            | No               | No                |
| MatterBot Github                                                                                 | RSS            | No               | No                |
| Microsoft Vulnerability & Threat Reports                                                         | RSS            | No               | No                |
| Morphisec Threat Intelligence                                                                    | RSS            | No               | No                |
| Nasjonal sikkerhetsmyndighet (NorCERT)                                                           | RSS            | No               | No                |
| Nationellt CSIRT Sverige                                                                         | RSS            | No               | No                |
| Netwitness Intelligence                                                                          | RSS            | No               | No                |
| Nextron Systems Blog                                                                             | RSS            | No               | No                |
| NCSC Netherlands Advisories                                                                      | RSS            | No               | No                |
| NCSC United Kingdom Advisories                                                                   | RSS            | No               | No                |
| Nemzeti Koordinációs Központ (NCSC-HU)                                                           | RSS            | No               | No                |
| Netskope Threat Labs                                                                             | RSS            | No               | No                |
| OffSec Threat Research                                                                           | RSS            | No               | No                |
| Okta Security                                                                                    | RSS            | No               | No                |
| Onapsis SAP Security                                                                             | RSS            | No               | No                |
| OpenCVE feed of CVEs                                                                             | RSS            | Yes              | No                |
| Orange Cyberdefense SensePost                                                                    | RSS            | No               | No                |
| Osint10x Blog / News                                                                             | RSS            | No               | No                |
| Outpost24 Threat Intelligence                                                                    | RSS            | No               | No                |
| Palo Alto/Unit 42 Advisories                                                                     | RSS            | No               | No                |
| Patchstack Wordpress Security                                                                    | RSS            | No               | No                |
| Persistent Security News                                                                         | RSS            | No               | No                |
| Portswigger Threat Research                                                                      | RSS            | No               | No                |
| Prodaft Threat Intelligence                                                                      | RSS            | No               | No                |
| Pulsedive Threat Intelligence                                                                    | RSS            | No               | No                |
| Qualys Threat Research                                                                           | RSS            | No               | No                |
| RansomLook (with support for detection of keywords/regex)                                        | JSON           | No               | No                |
| Ransomwatch                                                                                      | JSON           | No               | No                |
| Recorded Future Threat Research                                                                  | RSS            | No               | No                |
| Redcanary Security Blog                                                                          | RSS            | No               | No                |
| Reddit (configurable list of subreddits)                                                         | RSS            | No               | No                |
| RST Cloud Intelligence                                                                           | RSS            | No               | No                |
| S3 Eurom Research                                                                                | RSS            | No               | No                |
| SANS Internet Storm Center                                                                       | RSS            | No               | No                |
| SebDraven                                                                                        | RSS            | No               | No                |
| Synacktiv Threat Research                                                                        | RSS            | No               | No                |
| SecurityAffairs News                                                                             | RSS            | No               | No                |
| Sekoia Threat Intelligence                                                                       | RSS            | No               | No                |
| Snyk.io Security Blog                                                                            | RSS            | No               | No                |
| SOCPrime Threat Intelligence                                                                     | RSS            | No               | No                |
| Sophos X-Ops                                                                                     | RSS            | No               | No                |
| Specterops Security Blog                                                                         | RSS            | No               | No                |
| Spiceworks Tech News                                                                             | RSS            | No               | No                |
| Sploitus Exploits                                                                                | RSS            | No               | No                |
| Splunk Threat Research                                                                           | RSS            | No               | No                |
| Starlabs Threat Research                                                                         | RSS            | No               | No                |
| Sublime Security Blog                                                                            | RSS            | No               | No                |
| Thalium Threat Research                                                                          | RSS            | No               | No                |
| TheHackerNews News                                                                               | RSS            | No               | No                |
| The Record Media                                                                                 | RSS            | No               | No                |
| The DFIR-Report Blog                                                                             | RSS            | No               | No                |
| Threatanatomy Security Research                                                                  | RSS            | No               | No                |
| Threatmon Threat Intelligence                                                                    | RSS            | No               | No                |
| Threatpost News                                                                                  | RSS            | No               | No                |
| TrailOfBits Security Blog                                                                        | RSS            | No               | No                |
| TrendMicro Research                                                                              | RSS            | No               | No                |
| Tripwire State of Security                                                                       | RSS            | No               | No                |
| Trustedsec Offensive Security                                                                    | RSS            | No               | No                |
| Trustwave SpiderLabs                                                                             | RSS            | No               | No                |
| Tweakers.net Nieuws                                                                              | RSS            | No               | No                |
| US-CERT National Cyber Awareness System (Advisories, Alerts, Analysis Reports, Current Activity) | RSS            | No               | No                |
| Validin Threat Intelligence                                                                      | RSS            | No               | No                |
| Varonis Threat Research                                                                          | RSS            | No               | No                |
| Veeam Advisories                                                                                 | RSS            | No               | No                |
| Velociraptor News/Updates                                                                        | RSS            | No               | No                |
| Volexity Memory Forensics & Threat Intelligence Blog                                             | RSS            | No               | No                |
| Wallarm API Security                                                                             | RSS            | No               | No                |
| watchTowr Offensive Security Blog                                                                | RSS            | No               | No                |
| ESET WeLiveSecurity News                                                                         | RSS            | No               | No                |
| WikiJS Page Updates                                                                              | WikiJS GraphQL | Yes              | No                |
| Windows IR Blog                                                                                  | RSS            | No               | No                |
| Wiz.io Cloud Research                                                                            | RSS            | No               | No                |
| Xintra (Inversecos) Research Blog                                                                | RSS            | No               | No                |
| Yarix Threat Intelligence                                                                        | RSS            | No               | No                |
| Zero Day Initiative Upcoming Advisories                                                          | RSS            | No               | No                |
| Zetier Threat Intelligence                                                                       | RSS            | No               | No                |

New Matterfeed modules can be created. A boilerplate example can be found in the `modules` directory.

### `matterbot` Commands

The Matterbot component listens in a given set of channels (configurable per module) for user-definable commands, executes and returns the results of the module code. The currently supported commands are listed below:

| Name                                    | Type                       | Functionality / Use Case                                                                                                                                                                                                                                                                                                                                           | API Key Required                                                         | Paid Subscription                                                                                                                                                               |
| --------------------------------------- | -------------------------- |:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |:------------------------------------------------------------------------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| AbuseIPDB                               | Threat Intel               | Look up IPv4, IPv6 and netblocks for indicators/reports of abuse                                                                                                                                                                                                                                                                                                   | Yes                                                                      | No, but higher tier API rate limits are only available to paid subscribers                                                                                                      |
| AlienVault OTX                          | Threat Intel               | Look up IPv4, IPv6, hostnames, domains, MD5/SHA1/SHA256 hashes and URLs                                                                                                                                                                                                                                                                                            | No                                                                       | No, but some API limitations may apply                                                                                                                                          |
| Argos Translate                         | Documentation/Threat Intel | Offline translation model to translate strings                                                                                                                                                                                                                                                                                                                     | No                                                                       | No                                                                                                                                                                              |
| ASN WHOIS                               | Threat Intel               | Look up Autonomous System Numbers and return the ownership, peering and location information                                                                                                                                                                                                                                                                       | No                                                                       | No                                                                                                                                                                              |
| AttackMatrix                            | Threat Intel               | Query an [AttackMatrix](https://github.com/uforia/AttackMatrix) instance for e.g. MITRE ATT&CK IDs, Actor- and TTP-overlap. Requires Python GraphViz bindings to display the accompanying Graph                                                                                                                                                                    | No, unless the AttackMatrix API is configured to require an API key      | No                                                                                                                                                                              |
| Bootloaders                             | Threat Intel               | Query 'Bootloaders' project for vulnerable/malicious bootloader information. Returns detailed information, hashes and detection rules                                                                                                                                                                                                                              | No                                                                       | No                                                                                                                                                                              |
| Broadcom Symantec Security Cloud (BSSC) | Threat Intel               | Retrieve 'Threat Intel Insight' information for SHA256 file hashes, IPs, reputations, domains and URLs                                                                                                                                                                                                                                                             | Yes                                                                      | Yes                                                                                                                                                                             |
| Censys                                  | Threat Intel               | Query Censys for IPs and SHA256 certificate fingerprints. Query results are returned as the original Censys JSON blob                                                                                                                                                                                                                                              | Yes                                                                      | No: basic functionality<br />Yes: additional features, such as pagination                                                                                                       |
| ChatGPT                                 | LLM / GPT queries          | Ask OpenAI's ChatGPT singular questions (no  support for chat history). Requires a paid subscription with sufficient credits                                                                                                                                                                                                                                       | Yes                                                                      | Yes                                                                                                                                                                             |
| crt.sh                                  | Threat Intel               | Query crt.sh's repository for TLS certificates related to a domain name                                                                                                                                                                                                                                                                                            | No                                                                       | No                                                                                                                                                                              |
| Diceroll                                | Fun                        | Roll any kind of dice combination: #d# format                                                                                                                                                                                                                                                                                                                      | No                                                                       | No                                                                                                                                                                              |
| DNSDumpster                             | Threat Intel               | Query the DNSDumpster API for e.g. A, MX, NS, PTR records associated with a domain name                                                                                                                                                                                                                                                                            | Yes                                                                      | No: 50 queries per day<br />Yes: higher rate limits                                                                                                                             |
| DocGen                                  | Documentation              | Automatically create documentation with templated variables, rendering and more. Probably useless unless you have all the required materials.                                                                                                                                                                                                                      | No                                                                       | No                                                                                                                                                                              |
| Docspell                                | Documentation              | Query an existing Docspell collective for search terms(1)                                                                                                                                                                                                                                                                                                          | Yes                                                                      | Yes: there are no public instances, so you need to set this up yourself                                                                                                         |
| Early Warning & Advisory (EWA)          | Threat Intel               | Create Early Warning & Advisory documents using the National Vulnerability Database (NVD) and WikiJS information. Requires pandoc,  pypandoc, LaTeX, a WikiJS instance and a CSS template for final rendering                                                                                                                                                      | No (for NVD)<br />Yes (for WikiJS)                                       | No                                                                                                                                                                              |
| GeoLocation                             | Threat Intel               | Convert latitude/longitude  values into an address                                                                                                                                                                                                                                                                                                                 | No                                                                       | No                                                                                                                                                                              |
| GreyNoise                               | Threat Intel               | Query the GreyNoise API for IP address reputation, such as whether an IP has been observed scanning the internet,  source & destination countries, fingerprints, ports scanned, whether it is benign or not, etc.                                                                                                                                                  | Yes                                                                      | Yes: certain features require an additional subscription license, such as timeline and similarity features; see the GreyNoise website and API documentation or more information |
| GTFOBins                                | Threat Intel               | Query the *'~~Get The F**k~~ Break Out'* [binaries project] for file information. Can be used to escape from restricted shells, escalate or maintain elevated privileges, transfer files, spawn bind and reverse shells, and facilitate the other post-exploitation tasks. Returns detailed information and code examples, which can be used in detection patterns | No                                                                       | No                                                                                                                                                                              |
| HaveIBeenPwned                          | Threat Intel               | Query the HIBP project for information related to breaches                                                                                                                                                                                                                                                                                                         | Yes                                                                      | Yes                                                                                                                                                                             |
| Hybrid-Analysis                         | Threat Intel               | Look up IPs, hostnames, domains, URLs, MD5, SHA1, SHA256, Authentihash, Imphash, ssdeep hashes and VxFamily names, as well as known 'context' and 'similarity'                                                                                                                                                                                                     | Yes: 'vetted' API key strongly recommended to prevent hitting API limits | No: basic functionality, Yes: additional features/details                                                                                                                       |
| IPinfo                                  | Threat Intel               | Look up IP address information, such as geolocation and ownership                                                                                                                                                                                                                                                                                                  | Yes                                                                      | No: basic functionality, Yes: increased query limits                                                                                                                            |
| IPLocation                              | Threat Intel               | Look up general location information (country, ISP) for an IPv4 of IPv6 address                                                                                                                                                                                                                                                                                    | No                                                                       | No                                                                                                                                                                              |
| IPWHOIS                                 | Threat Intel               | Look up IP address information: ownership, ASN, geolocation information                                                                                                                                                                                                                                                                                            | No                                                                       | No                                                                                                                                                                              |
| KoboldCPP                               | AI                         | Query a KoboldCPP instance with a question                                                                                                                                                                                                                                                                                                                         | Yes                                                                      | Yes: either a paid subscription with an existing provider, or requires your own resource                                                                                        |
| LeakIX                                  | Threat Intel               | Find subdomains and look up possible information/data leaks for hosts and domains                                                                                                                                                                                                                                                                                  | Yes: API key strongly recommended to prevent hitting API limits          | No: basic functionality, Yes: additional data                                                                                                                                   |
| LOLBAS                                  | Threat Intel               | Query the 'Living Off The Land Binaries, Scripts and Libraries' project for file information. Returns detailed information and detection rules                                                                                                                                                                                                                     | No                                                                       | No                                                                                                                                                                              |
| LOLDrivers                              | Threat Intel               | Query 'Living Off The Land Drivers' project for driver information. Returns detailed information, hashes and detection rules                                                                                                                                                                                                                                       | No                                                                       | No                                                                                                                                                                              |
| MACVendors                              | Threat Intel               | Query the IEEE Standards Association MAC Address database. Returns vendor of specified address                                                                                                                                                                                                                                                                     | No, but is limited to 1 request per second per 1k requests per day       | No                                                                                                                                                                              |
| Malpedia                                | Threat Intel               | Look up malware families, threat actors and MD5/SHA256 malware hashes                                                                                                                                                                                                                                                                                              | No: basic functionality<br />Yes: malware downloads                      | No                                                                                                                                                                              |
| MalwareBazaar                           | Threat Intel               | Query MalwareBazaar for MD5/SHA1/SHA256 hashes of malware. Will also return include a downloadable malware sample, if available                                                                                                                                                                                                                                    | No                                                                       | No                                                                                                                                                                              |
| MISP                                    | Threat Intel               | Search a MISP instance for the given search terms, e.g. exact (not partial!) IoCs. Returns links to the MISP Events where the search terms have been found.                                                                                                                                                                                                        | Yes                                                                      | No                                                                                                                                                                              |
| MWDB                                    | Threat Intel               | Query your own or the CERT.pl MWDB instance for information on malware samples, malware configs or text blobs extracted from malware                                                                                                                                                                                                                               | Yes                                                                      | No                                                                                                                                                                              |
| OpenCVE                                 | Vulnerability Management   | Query an OpenCVE instance for information about vulnerabilities.                                                                                                                                                                                                                                                                                                   | Yes                                                                      | No                                                                                                                                                                              |
| Ollama                                  | AI                         | Query an Ollama instance with a question                                                                                                                                                                                                                                                                                                                           | Yes                                                                      | Yes: either a paid subscription with an existing provider, or requires your own resources                                                                                       |
| Qualys                                  | Vulnerability Management   | Query the Qualys CSAM API for software/libraries present on systems. Extremely useful for Attack Surface Management / Vulnerability Management. Returns a collated dataset of found software and versions, as well as a CSV list of systems found                                                                                                                  | Yes                                                                      | Yes: Qualys subscription required, as well as CSAM subscription and agent-based scans on hosts                                                                                  |
| RansomLook                              | Threat Intel               | Search and view ransomware groups, markets, posts and telegram channels                                                                                                                                                                                                                                                                                            | No                                                                       | No                                                                                                                                                                              |
| ReversingsLabs A1000 / TitaniumCloud    | Threat Intel               | Look up IPv4, IPv6, hosts/domains, URLs and MD5/SHA1/SHA256/SHA512 hashes                                                                                                                                                                                                                                                                                          | Yes                                                                      | Yes                                                                                                                                                                             |
| RIPE WHOIS                              | Threat Intel               | Look up IP address information: ownership, CIDR and geolocation information                                                                                                                                                                                                                                                                                        | No                                                                       | No                                                                                                                                                                              |
| Shodan                                  | Threat Intel               | Query Shodan for IP address or host information, as well as performing `count` and `search` queries. Results will include the original Shodan JSON blob as a download                                                                                                                                                                                              | Yes                                                                      | No: basic functionality<br />Yes: pagination, search queries, etc.                                                                                                              |
| SSLMate                                 | Threat Intel               | Look up SSL/TLS SHA256 hashes in the Certificate Transparency logs. Returns historic data, related hostnames, revocation status and validity times                                                                                                                                                                                                                 | Yes                                                                      | No                                                                                                                                                                              |
| ThreatFox                               | Threat Intel               | Query ThreatFox for MD5/SHA1/SHA256 hashes, IP addresses                                                                                                                                                                                                                                                                                                           | No                                                                       | No                                                                                                                                                                              |
| TLSGrab                                 | Threat Intel               | Connect to the given IP address + port, and attempt to retrieve the TLS certificate CNs. *Note: this is an OPSEC risk, because the bot will actively attempt to connect to the host/port!*                                                                                                                                                                         | No                                                                       | No                                                                                                                                                                              |
| Tria.ge                                 | Threat Intel               | Search the tria.ge sandbox project for IPv4, IPv6, domains, urls, hashes, a Tria.ge ID, etc. Responses may include the malware sample, if available                                                                                                                                                                                                                | Yes                                                                      | No: basic functionality<br />Yes: additional information                                                                                                                        |
| Tweetfeed                               | Threat Intel               | Query the Tweetfeed API for the given IoC/tag                                                                                                                                                                                                                                                                                                                      | No                                                                       | No                                                                                                                                                                              |
| Unprotect.it                            | Threat Intel               | Search the Unprotect.it project for information on TTPs, code snippets and detection rules. Returns code snippets and detection rules as a download, if available                                                                                                                                                                                                  | No                                                                       | No                                                                                                                                                                              |
| URLhaus                                 | Threat Intel               | Look up reputation info on URLhaus for URLs and MD5 / SHA1 / SHA256 URL hashes                                                                                                                                                                                                                                                                                     | No                                                                       | No                                                                                                                                                                              |
| VirusTotal                              | Threat Intel               | Search VirusTotal for IP addresses, MD5/SHA1/SHA256 hashes, URLs and domains. Returned results will include maliciousness, TTP sets, malware family names, etc., if available                                                                                                                                                                                      | Yes                                                                      | No: basic functionality<br />Yes: paid VT features, throttling limit removal, etc.                                                                                              |
| WikiJS                                  | Information Retrieval      | Search through WikiJS pages' contents for the given search terms. Returns links to the pages where the contents were found                                                                                                                                                                                                                                         | Yes                                                                      | Yes: currently requires a Microsoft Azure Search instance that indexes the WikiJS instance (*Note: this is a WikiJS limitation!*)                                               |

*(1) It is not possible to for the author(s) to share access to their own Docspell instances or any paid online resources. Please do not ask for this and be understanding, thank you!*

New Matterbot modules can be created. A boilerplate example can be found in the `commands` directory.

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
