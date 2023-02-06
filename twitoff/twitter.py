"""Retrieve Tweets, embeddings, and persist in the database."""
from os import getenv

import not_tweepy as tweepy
import spacy

from twitoff.models import DB, Tweet, User

# https://greatist.com/happiness/must-follow-twitter-accounts
TWITTER_USERS = ('calebhicks', 'elonmusk', 'rrherr', 'SteveMartinToGo',
                 'alyankovic', 'NASA', 'jkhowland', 'Austen',
                 'common_squirrel', 'KenJennings', 'ConanOBrien',
                 'big_ben_clock', 'IAM_SHAKESPEARE')
TWITTER_AUTH = tweepy.OAuth1UserHandler(getenv('TWITTER_API_KEY'),
                                        getenv('TWITTER_API_SECRET'))
TWITTER = tweepy.API(TWITTER_AUTH)

# loading in nlp model and returning 300 size embedding
nlp = spacy.load('en_core_web_sm')


def vectorize_tweet(tweet_text):
    return nlp(tweet_text).vector


def add_or_update_user(username):
    """Add or update a user and their Tweets, error if not a Twitter user."""
    try:
        twitter_user = TWITTER.get_user(username)
        db_user = (User.query.get(twitter_user.id) or
                   User(id=twitter_user.id, name=username))
        DB.session.add(db_user)
        # We want as many recent non-retweet/reply statuses as we can get
        # 200 is a Twitter API limit, we'll usually see less due to exclusions
        tweets = twitter_user.timeline(
            count=200, exclude_replies=True, include_rts=False,
            tweet_mode='extended', since_id=db_user.newest_tweet_id)
        if tweets:
            db_user.newest_tweet_id = tweets[0].id
        for tweet in tweets:
            # Calculate embedding on the full tweet, but truncate for storing
            # embedding now uses spacy
            embedding = vectorize_tweet(tweet.full_text)
            db_tweet = Tweet(id=tweet.id, text=tweet.full_text[:300],
                             embedding=embedding)
            db_user.tweets.append(db_tweet)
            DB.session.add(db_tweet)
    except Exception as e:
        print('Error processing {}: {}'.format(username, e))
        raise e
    else:
        DB.session.commit()


def add_users(users=TWITTER_USERS):
    """
    Add/update a list of users (strings of usernames).
    May take a while, so run "offline" (flask shell).
    """
    for user in users:
        add_or_update_user(user)


def update_all_users():
    """Update all Tweets for all Users in the User table."""
    for user in User.query.all():
        add_or_update_user(user.name)
