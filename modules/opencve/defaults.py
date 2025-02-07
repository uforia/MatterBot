#!/usr/bin/env python3

NAME = "OpenCVE Feed"
CHANNELS = (
    "newsfeed",
)
# Your OpenCVE instance. You may use the public OpenCVE API as well, but
# be aware of rate limits. It is strongly recommended to setup your own
# OpenCVE instance.
URL = "https://<your-opencve-instance-here>"
# If you want to link to the public OpenCVE descriptions, change this to
# 'True'
PUBLICDESCURL = True
# API endpoint URL
API = "/api"
# Username and password to connect to the API endpoint.
USERNAME = "<your-opencve-username>"
PASSWORD = "<your-opencve-password>"
# Number of entries to consider
ENTRIES = 30
# Lookback window: only consider CVEs that are less old than this setting (months)
LOOKBACK = 3
# What's the minimum CVSS score we should consider? Set to '0.0' to see
# every single CVSS (noisy!).
THRESHOLD = 6.0
# Should we focus only on CVEs from this year?
RECENTONLY = True
# Should we display CVEs without a CVSS score?
NOCVSS = False
# Title filter: ignore all vulnerabilities with any of the following words
# in them (can be a regex, see examples below). This is useful if you are
# not interested in particular products/versions/brands/companies/etc. and
# want to filter those out.
PRODUCTFILTER = (
    r'[wW]ordpress',
    r'[pP]lugin',
)
# The AUTOADVISORY feature is really only useful if you are using other
# related bot modules, such as Qualys, and the bot can 'call itself'.
# E.g.: you would need something like '@qualys sw' as the command.
# The bot will append the product name to the command, to tell itself to
# check if any assets are using the product/software/vendor in question.
# True = enabled, False = disabled
AUTOADVISORY = False
# Format: 'channel name': [ 'command1', 'command2', ... ]
ADVISORYCHANS = {
}
# Consider all CVEs with a score above this value. Prevents noise and helps
# focusing on the high/criticals only for the AUTOADVISORY FEATURE.
ADVISORYTHRESHOLD = 7.0
# History file used to prevent double-posting.
HISTORY = "history.cache"
