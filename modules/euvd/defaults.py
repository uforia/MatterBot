#!/usr/bin/env python3

NAME = "European Union Vulnerability Database"
CHANNELS = (
    "newsfeed",
)
CATEGORIES = {
    'Recent': 'https://euvdservices.enisa.europa.eu/api/lastvulnerabilities',
    'Exploited': 'https://euvdservices.enisa.europa.eu/api/exploitedvulnerabilities',
    'Critical': 'https://euvdservices.enisa.europa.eu/api/criticalvulnerabilities',
}
TOPICS = (
    "Vulnerabilities",
)
BASEDETAILURL = 'https://euvd.enisa.europa.eu/vulnerability/'
ADMIN_ONLY = False
CONTENTTYPE = 'application/json'
ENTRIES = 8 # EUVD limits the 'feed-style' API results to a maximum 8 results
