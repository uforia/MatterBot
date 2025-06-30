#!/usr/bin/env python3

NAME = "RansomLook Post"
URL = "http://www.ransomlook.io/api/recent"
CHANNELS = (
    "newsfeed",
)
TOPICS = (
    "CTI",
)
ADMIN_ONLY = False
ENTRIES = 10
# Specific keywords you want to notify for and in which channel the notifications go
KEYWORDS = {
    "<special word 1>": "<private-channel>",
    "<regex 2>": "<other-private-channel>",
}
# Set to `True` to have the bot download and attach available screenshot to posts
SCREENDL = True

