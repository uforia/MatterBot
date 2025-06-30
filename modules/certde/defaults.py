#!/usr/bin/env python3

NAME = "CERT Bundesrepublik Deutschland"
URLS = (
    "https://wid.cert-bund.de/content/public/securityAdvisory/rss",
    "https://www.bsi.bund.de/SiteGlobals/Functions/RSSFeed/RSSNewsfeed/RSSNewsfeed_CSW.xml"
)
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Government",
    "Vulnerabilities"
)
ENTRIES = 10
TRANSLATION = True
ADMIN_ONLY = False