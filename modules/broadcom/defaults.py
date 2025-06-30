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
    "Enterprise Software",
    "Threat Intelligence",
    "Vulnerabilities"
)
ENTRIES = 10
ADMIN_ONLY = False