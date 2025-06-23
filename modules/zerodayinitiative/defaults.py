#!/usr/bin/env python3
from datetime import datetime
year = datetime.now().year
NAME = "Zero Day Initiative Upcoming Vulnerabilities"
URLS = (
    "https://www.zerodayinitiative.com/rss/upcoming/",
    f"https://www.zerodayinitiative.com/rss/published/{year}/"
    )
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "Vulnerabilities"
)
ENTRIES = 10
