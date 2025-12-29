#!/usr/bin/env python3

NAME = "Siemens Product Advisories"
URL = "https://cert-portal.siemens.com/productcert/csaf/ssa-feed-tlp-white.json"
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "Advisories",
    "OT",
    "Vendor",
    "Vulnerabilities"
)
ADMIN_ONLY = False
ENTRIES = 10
FILTER = False # Filter entries for cvss scores
