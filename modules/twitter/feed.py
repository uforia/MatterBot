#!/usr/bin/env python3

# Every module must set the CHANNEL variable to indicate where information should be sent to in Mattermost
#
# Every module must implement the query() function.
# This query() function is called by the main worker and has only one parameter: the number of historic
# items that should be returned in the list.
#
# Every module must return a list [...] with 0, 1 ... n entries
# of 2-tuples: ('<channel>', '<content>')
#
# <channel>: basically the destination channel in Mattermost, e.g. 'Newsfeed', 'Incident', etc.
# <content>: the content of the message, MD format possible

import datetime
import logging
import tweepy
import json
from pathlib import Path
try:
    from modules.twitter import defaults as settings
except ModuleNotFoundError: # local test run
    import defaults as settings
    if Path('settings.py').is_file():
        import settings
else:
    if Path('modules/twitter/settings.py').is_file():
        try:
            from modules.twitter import settings
        except ModuleNotFoundError: # local test run
            import settings

def query(MAX=0):
    client = tweepy.Client(settings.BEARER_TOKEN)
    tweets_list = []
    user_id = client.get_user(username=settings.USERNAME).data.id
    follows = client.get_users_following(user_id).data
    for follow in follows:
        follow_id = follow.id
        tweets = client.get_users_tweets(id=follow_id, max_results=settings.HISTORY, tweet_fields=['created_at', 'id'])
        username = client.get_user(id=follow_id).data.username
        if tweets.data != None:
            for tweet in tweets.data:
                tweets_list.append({'username': username, 'url': 'https://twitter.com/' + username + '/status/' + str(tweet.id), 'text': tweet.text, 'timestamp': tweet.created_at.strftime('%H:%M:%S UTC')})
    items = []
    for tweet in tweets_list:
        username = '@[' + tweet['username'] + '](https://twitter.com/' + tweet['username'] + ')'
        text = tweet['text']
        url = tweet['url']
        timestamp = tweet['timestamp']
        content = username + ' [tweet](' + url + '): ' + text + ' at ' + timestamp
        items.append([settings.CHANNEL, content])
    if len(items)>0:
        return items

if __name__ == "__main__":
    print(query())
