#!/usr/bin/env python3
from datetime import datetime

NAME = "Zero Day Initiative Upcoming Advisories"
CHANNELS = (
    "newsfeed",
)
year = datetime.now().year
URLS = (
    "https://www.zerodayinitiative.com/rss/upcoming/",
    f"https://www.zerodayinitiative.com/rss/published/{year}/"
    )
ENTRIES = 10
