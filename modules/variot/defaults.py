#!/usr/bin/env python3

NAME = "VARIoT Feed"
# Your OpenCVE instance. You may use the public OpenCVE API as well, but
# be aware of rate limits. It is strongly recommended to setup your own
# OpenCVE instance.
URL = "https://www.variotdbs.pl/api/vulns/"
KEY = "<your-variot-api-key>"
CHANNELS = (
    "vulnerabilities",
)
TOPICS = (
    "Vulnerabilities",
)
ADMIN_ONLY = True
ENTRIES = 30
CONTENTTYPE = 'application/json'
HISTORY = "history.cache"