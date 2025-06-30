#!/usr/bin/env python3

NAME = "Broadcom Symantec"
URLS = (
    "https://sed-cms.broadcom.com/rss/v1/blogs/rss.xml/221", # Threat intelligence
    "https://sed-cms.broadcom.com/rss/v1/blogs/rss.xml/16254" # SolarWinds research
)
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Software",
    "CTI",
    "Vulnerabilities"
)
ADMIN_ONLY = False
ENTRIES = 10