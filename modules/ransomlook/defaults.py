#!/usr/bin/env python3

NAME = "RansomLook Post"
CHANNELS = (
    "newsfeed",
)
URL = "http://www.ransomlook.io/api/recent"
ENTRIES = 10
# Specific keywords you want to notify for and in which channel the notifications go
KEYWORDS = {
    "<special word 1>": "<private-channel>",
    "<regex 2>": "<other-private-channel>",
}