#!/usr/bin/env python3

NAME = "Kyberturvallisuuskeskuksen Suomi (NCSC-FI)"
URLS = (
    "https://www.kyberturvallisuuskeskus.fi/feed/rss/en/399",                   # Newsletter
    "https://www.kyberturvallisuuskeskus.fi/sites/default/files/rss/news.xml"   # External threat intelligence sources
)
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "General",
    "Government",
    "Posture"
)
ADMIN_ONLY = False
ENTRIES = 10
