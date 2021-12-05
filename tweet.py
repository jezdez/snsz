#!/usr/bin/env python
import os
import time

import feedparser
import structlog
import tweepy
from diskcache import Index

here = os.path.dirname(__file__)
logger = structlog.get_logger()

TWITTER_BEARER_TOKEN = os.environ["TWITTER_BEARER_TOKEN"]
TWITTER_CONSUMER_KEY = os.environ["TWITTER_CONSUMER_KEY"]
TWITTER_CONSUMER_SECRET = os.environ["TWITTER_CONSUMER_SECRET"]
TWITTER_ACCESS_TOKEN = os.environ["TWITTER_ACCESS_TOKEN"]
TWITTER_ACCESS_TOKEN_SECRET = os.environ["TWITTER_ACCESS_TOKEN_SECRET"]
RSS_FEED_PATH = os.path.join(here, "website", "data", "schools.rss")
TWEET_CACHE = os.path.join(here, "cache", "tweets")

os.makedirs(TWEET_CACHE, exist_ok=True)
tweets = Index(TWEET_CACHE)

twitter = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_CONSUMER_KEY,
    consumer_secret=TWITTER_CONSUMER_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
)

# get all the entries we want
entries = feedparser.parse(RSS_FEED_PATH)["entries"]


def send_tweet(entry, text):
    """
    send tweet for given feed entry
    """
    logger.info("Tweet text", entry=entry, text=text)
    return twitter.create_tweet(text=text)


# iterate over RSS feed entries and see if we need to tweet
for entry in entries:
    # fetch article data
    guid = entry["id"]
    text = f"""{entry["title"]}

{entry["description"]}

Mehr Infos: {entry["link"]}
"""
    entry_last_tweeted = tweets.get(guid)
    if (
        entry_last_tweeted is not None
        and entry_last_tweeted != text
        and not entry_last_tweeted.startswith("Update: ")
    ):
        text = f"Update: {text}"

    try:
        response = send_tweet(entry, text)
    except tweepy.Forbidden:
        # raised if tweet is the same as last one, no need to tweet again
        logger.info("Forbidden response found", entry=entry)
    except tweepy.TooManyRequests:
        logger.exception("Rate-limiting response found", entry=entry)
        break
    except Exception:
        logger.exception("Tweet failed", entry=entry, response=response)
    else:
        tweets[guid] = text
        logger.info("Tweet successful", entry=entry, text=text)
        # let's sleep a bit to not overwhelm the Twitter API
        time.sleep(0.5)
