import os
import logging
import datetime

from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import mail

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp import template

from libs import tweepy
from settings import *

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


# OpenID Login
class TwitterReturnView(webapp.RequestHandler):
    def get(self):
        verifier = self.request.get('oauth_verifier')

        # we need to re-build the auth handler
        # first...
        auth = tweepy.OAuthHandler(TWITTER_OAUTH_CONSUMER_TOKEN, \
                TWITTER_OAUTH_CONSUMER_SECRET)

        key = memcache.get('request_token_key')
        sec = memcache.get('request_token_secret')

        auth.set_request_token(key, sec)

        try:
            token = auth.get_access_token(verifier)
            logging.info("token: %s" % str(token))
        except tweepy.TweepError:
            print 'Error! Failed to get access token.'
