#!/usr/bin/env python3

NAME = "Canadian Centre for Cyber Security"
URLS = (
    "https://www.cyber.gc.ca/api/cccs/rss/v1/get?feed=alerts_advisories",
    "https://www.cyber.gc.ca/api/cccs/rss/v1/get?feed=news_events_guidance"
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
ADMIN_ONLY = False