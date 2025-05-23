#!/usr/bin/env python3

NAME = "Fortinet PSIRT/Threat Research Blogs"
CHANNELS = (
    "newsfeed",
)
URLS = (
    "https://feeds.fortinet.com/fortinet/blog/psirt", 
    "https://filestore.fortinet.com/fortiguard/rss/ir.xml",
    "https://filestore.fortinet.com/fortiguard/rss/outbreakalert.xml",
    "https://filestore.fortinet.com/fortiguard/rss/threatsignal.xml",
    "https://feeds.fortinet.com/fortinet/blog/threat-research"
)

ENTRIES = 10
FILTER = False # Filter entries for cvss scores (pretty noisy)