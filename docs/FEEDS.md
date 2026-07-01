# MatterBot — `matterfeed` Sources

[← Back to README](../README.md)

`matterfeed` aggregates news/advisory sources on a schedule and posts updates to a
channel. Every source is a module under `modules/`, categorized in one or more
topic(s); users can subscribe/unsubscribe per source or per topic.

The currently supported sources are listed below:

| Name                                                                                             | Type           | API Key Required | Paid Subscription |
| ------------------------------------------------------------------------------------------------ |:--------------:|:----------------:|:-----------------:|
| 0dayfans Security News                                                                           | RSS            | No               | No                |
| 1275 Новости (RU)                                                                                | RSS            | No               | No                |
| ABB Advisories                                                                                   | RSS            | No               | No                |
| Akamai Security Blog                                                                             | RSS            | No               | No                |
| Any.run Cybersecurity Blog                                                                       | RSS            | No               | No                |
| Aqua Security Blog                                                                               | RSS            | No               | No                |
| Arctic Wolf Security Blog                                                                        | RSS            | No               | No                |
| Asec Ahnlab Threat Intelligence                                                                  | RSS            | No               | No                |
| Attackiq Threat Intelligence                                                                     | RSS            | No               | No                |
| Australian Cyber Security Centre                                                                 | RSS            | No               | No                |
| Bad Sector Labs Newsletter                                                                       | RSS            | No               | No                |
| Barracuda Threat Intelligence                                                                    | RSS            | No               | No                |
| Binary Defense                                                                                   | RSS            | No               | No                |
| Bishop Fox Offensive Security                                                                    | RSS            | No               | No                |
| Bleepingcomputer News                                                                            | RSS            | No               | No                |
| Bluesky Social Network                                                                           | RSS            | No               | No                |
| Breakglass Intelligence Blog                                                                     | RSS            | No               | No                |
| Broadcom Symantec                                                                                | RSS            | No               | No                |
| Bruce Schneier's Blog                                                                            | RSS            | No               | No                |
| Canadian Centre for Cyber Security                                                               | RSS            | No               | No                |
| CERT Bundesrepublik Deutschland                                                                  | RSS            | No               | No                |
| CERT Česká Republika                                                                             | RSS            | No               | No                |
| CERT Eesti Vabariik                                                                              | RSS            | No               | No                |
| CERT European Union                                                                              | RSS            | No               | No                |
| CERT Groussherzogtum Lëtzebuerg                                                                  | RSS            | No               | No                |
| CERT Instituto Nacional de Ciberseguridad                                                        | RSS            | No               | No                |
| CERT Latvijas Republika                                                                          | RSS            | No               | No                |
| CERT Republica Moldova                                                                           | RSS            | No               | No                |
| CERT Repubblica Italiana                                                                         | RSS            | No               | No                |
| CERT Republik Österreich                                                                         | RSS            | No               | No                |
| CERT Republika e Shqipërisë (AL)                                                                 | RSS            | No               | No                |
| CERT Republika Slovenija                                                                         | RSS            | No               | No                |
| CERT République Française                                                                        | RSS            | No               | No                |
| CERT Rzeczpospolita Polska                                                                       | RSS            | No               | No                |
| CERT Slovenská republika                                                                         | RSS            | No               | No                |
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
| Citrix Netscaler Blog                                                                            | RSS            | No               | No                |
| Claroty Vulnerability Disclosures                                                                | RSS            | No               | No                |
| Cloudseclist Newsletter                                                                          | RSS            | No               | No                |
| Cqure Blog                                                                                       | RSS            | No               | No                |
| CSHub (configurable list of CSHub feeds)                                                         | RSS            | No               | No                |
| Cybereason Threat Intelligence                                                                   | RSS            | No               | No                |
| Cyble Threat Intelligence                                                                        | RSS            | No               | No                |
| DarkNet Blog                                                                                     | RSS            | No               | No                |
| Darkowl Darkweb Intelligence                                                                     | RSS            | No               | No                |
| Darkrelay Offensive Security Blog                                                                | RSS            | No               | No                |
| DataBreaches.Net News                                                                            | RSS            | No               | No                |
| DataBreachToday News                                                                             | RSS            | No               | No                |
| Datadog Security Labs                                                                            | RSS            | No               | No                |
| Datalekt.nl Nieuwsfeed                                                                           | RSS            | No               | No                |
| Deepinstinct Threat Intelligence                                                                 | RSS            | No               | No                |
| DeiC Sikkerhed/DKCERT                                                                            | RSS            | No               | No                |
| Deutsche Telekom CERT                                                                            | RSS            | No               | No                |
| DIVD CSIRT                                                                                       | RSS            | No               | No                |
| Dragos OT Security                                                                               | RSS            | No               | No                |
| Eclecticiq Intelligence Research                                                                 | RSS            | No               | No                |
| Eclypsium Threat Research                                                                        | RSS            | No               | No                |
| Elastic Security Labs                                                                            | RSS            | No               | No                |
| European Union Vulnerability Database                                                            | JSON           | No               | No                |
| F5 Labs Threat Intelligence                                                                      | RSS            | No               | No                |
| FalconForce                                                                                      | RSS            | No               | No                |
| FieldEffect Threat Intelligence                                                                  | RSS            | No               | No                |
| Forescout Cyber Alerts                                                                           | RSS            | No               | No                |
| Fortinet PSIRT/Threat Research Blogs                                                             | RSS            | No               | No                |
| GBHackers News                                                                                   | RSS            | No               | No                |
| Gendigital Threat Research                                                                       | RSS            | No               | No                |
| Google Cloud Threat Intelligence                                                                 | RSS            | No               | No                |
| Google Security Blog                                                                             | RSS            | No               | No                |
| GreyNoise Threat Intelligence                                                                    | RSS            | No               | No                |
| Group-IB Blog                                                                                    | RSS            | No               | No                |
| Hacktron AI Threat Research                                                                      | RSS            | No               | No                |
| Hadrian Security Blog                                                                            | RSS            | No               | No                |
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
| Kela Cyber Threat Intelligence                                                                   | RSS            | No               | No                |
| Kitploit Tool Updates                                                                            | RSS            | No               | No                |
| KnowBe4 News                                                                                     | RSS            | No               | No                |
| KQLQuery Blog                                                                                    | RSS            | No               | No                |
| KrebsOnSecurity Blog                                                                             | RSS            | No               | No                |
| Kyberturvallisuuskeskuksen Suomi (NCSC-FI)                                                       | RSS            | No               | No                |
| Lab52 Threat Intelligence                                                                        | RSS            | No               | No                |
| Lumen Black Lotus Labs                                                                           | RSS            | No               | No                |
| MajorLeagueHacking News                                                                          | RSS            | No               | No                |
| Mastodon Social Network                                                                          | RSS            | No               | No                |
| MatterBot Github                                                                                 | RSS            | No               | No                |
| Microsoft Vulnerability & Threat Reports                                                         | RSS            | No               | No                |
| Morphisec Threat Intelligence                                                                    | RSS            | No               | No                |
| Nasjonal sikkerhetsmyndighet (NorCERT)                                                           | RSS            | No               | No                |
| Nationellt CSIRT Sverige                                                                         | RSS            | No               | No                |
| Netwitness Intelligence                                                                          | RSS            | No               | No                |
| Nextron Systems Blog                                                                             | RSS            | No               | No                |
| NCSC Nederland Nieuws                                                                            | RSS            | No               | No                |
| NCSC Nederland Advisories                                                                        | RSS            | No               | No                |
| NCSC United Kingdom Advisories                                                                   | RSS            | No               | No                |
| Nemzeti Koordinációs Központ (NCSC-HU)                                                           | RSS            | No               | No                |
| Netskope Threat Labs                                                                             | RSS            | No               | No                |
| Nozomi Networks Advisories                                                                       | RSS            | No               | No                |
| NVISO Blog                                                                                       | RSS            | No               | No                |
| OffSec Threat Research                                                                           | RSS            | No               | No                |
| Offseq Threat Feed                                                                               | RSS            | No               | No                |
| Okta Security                                                                                    | RSS            | No               | No                |
| Onapsis SAP Security                                                                             | RSS            | No               | No                |
| OpenCVE feed of CVEs                                                                             | RSS            | Yes              | No                |
| Opensource Malware Threat Intelligence                                                           | RSS            | Yes              | No                |
| Orange Cyberdefense SensePost                                                                    | RSS            | No               | No                |
| Osint10x Blog / News                                                                             | RSS            | No               | No                |
| Outpost24 Threat Intelligence                                                                    | RSS            | No               | No                |
| OX Security Blog                                                                                 | RSS            | No               | No                |
| Palo Alto/Unit 42 Advisories                                                                     | RSS            | No               | No                |
| Patchstack Wordpress Security                                                                    | RSS            | No               | No                |
| Persistent Security News                                                                         | RSS            | No               | No                |
| Portswigger Threat Research                                                                      | RSS            | No               | No                |
| Prodaft Threat Intelligence                                                                      | RSS            | No               | No                |
| Pulsedive Threat Intelligence                                                                    | RSS            | No               | No                |
| Qualys Threat Research                                                                           | RSS            | No               | No                |
| Quesma LLM Blog                                                                                  | RSS            | No               | No                |
| R136a1 Malware Analysis                                                                          | RSS            | No               | No                |
| RansomLook (with support for detection of keywords/regex)                                        | JSON           | No               | No                |
| Ransomwatch                                                                                      | JSON           | No               | No                |
| Recorded Future Threat Research                                                                  | RSS            | No               | No                |
| Red Asgard Threat Intelligence                                                                   | RSS            | No               | No                |
| Redcanary Security Blog                                                                          | RSS            | No               | No                |
| Reddit (configurable list of subreddits)                                                         | RSS            | No               | No                |
| Red Hat Product Advisories                                                                       | RSS            | No               | No                |
| Reliaquest Security Blog                                                                         | RSS            | No               | No                |
| RST Cloud Intelligence                                                                           | RSS            | No               | No                |
| runZero Threat Intelligence                                                                      | RSS            | No               | No                |
| S3 Eurom Research                                                                                | RSS            | No               | No                |
| SANS Internet Storm Center                                                                       | RSS            | No               | No                |
| Safedep Threat Intelligence                                                                      | RSS            | No               | No                |
| Searchlight Security Research                                                                    | RSS            | No               | No                |
| Security.nl Nieuws                                                                               | RSS            | No               | No                |
| SebDraven                                                                                        | RSS            | No               | No                |
| Securitylab Новости (RU)                                                                         | RSS            | No               | No                |
| SecurityAffairs News                                                                             | RSS            | No               | No                |
| Sekoia Threat Intelligence                                                                       | RSS            | No               | No                |
| Sick Advisories                                                                                  | RSS            | No               | No                |
| Siemens Product Advisories                                                                       | JSON           | No               | No                |
| SilentPush Threat Intelligence                                                                   | RSS            | No               | No                |
| Silobreaker Intelligence Blog                                                                    | RSS            | No               | No                |
| Snyk.io Security Blog                                                                            | RSS            | No               | No                |
| Socket.dev Blog                                                                                  | RSS            | No               | No                |
| SOCPrime Threat Intelligence                                                                     | RSS            | No               | No                |
| Sonicwall Advisories                                                                             | RSS            | No               | No                |
| Sophos Threat Research                                                                           | RSS            | No               | No                |
| Specterops Security Blog                                                                         | RSS            | No               | No                |
| Spiceworks Tech News                                                                             | RSS            | No               | No                |
| Sploitus Exploits                                                                                | RSS            | No               | No                |
| Splunk Threat Research                                                                           | RSS            | No               | No                |
| Starlabs Threat Research                                                                         | RSS            | No               | No                |
| StepSecurity Security Blog                                                                       | RSS            | No               | No                |
| Sublime Security Blog                                                                            | RSS            | No               | No                |
| Synacktiv Threat Research                                                                        | RSS            | No               | No                |
| Synaptic Security Blog                                                                           | RSS            | No               | No                |
| Sysdig Threat Research                                                                           | RSS            | No               | No                |
| Thalium Threat Research                                                                          | RSS            | No               | No                |
| TheHackerNews News                                                                               | RSS            | No               | No                |
| The Record Media                                                                                 | RSS            | No               | No                |
| The DFIR-Report Blog                                                                             | RSS            | No               | No                |
| Threatanatomy Security Research                                                                  | RSS            | No               | No                |
| Threatfabric Mobile                                                                              | RSS            | No               | No                |
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
| Volerion Threat Intelligence                                                                     | RSS            | No               | No                |
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
Every module is categorized in one or more topic(s). Users can subscribe or unsubscribe to specific newsfeeds or to a whole topic.
