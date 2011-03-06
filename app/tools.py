import re
import logging
import unicodedata
from operator import itemgetter
from urllib import urlopen

from google.appengine.api import memcache
from django.utils import simplejson as json

import akismet
from libs import tweepy

from models import *

import mc
import settings

_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')


"""
This file contains common tools.
All BSD licensed.
"""


def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    From Django's "django/template/defaultfilters.py".
    """
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)


def decode(var):
    """Decode form input"""
    if not var:
        return var
    return unicode(var, 'utf-8') if isinstance(var, str) else unicode(var)


def is_valid_email(email):
    if email and len(email) > 7 and re.match( \
        "^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", \
        email):
        return True
    return False


def send_message(sender, to, subject, message):
    """Build a new message which shows up when the recipient gets online.

    'to' can be a UserPrefs or an int for a group (10=all admins)
    """
    if type(to) in [int, long]:
        groupmembers = InternalUser.all().filter("level >=", to)
        for prefs in groupmembers:
            msg = Message()
            msg.sender = sender
            msg.recipient = prefs
            msg.recipient_group = to
            msg.subject = subject
            msg.message = message
            msg.put()

            prefs.messages_unread += 1
            prefs.put()

            logging.info("message '%s' sent to %s" % (subject, prefs.nickname))

    elif type(to) == type(InternalUser):
        msg = Message()
        msg.sender = sender
        mss.recipient = to
        msg.subject = subject
        msg.message = message
        msg.put()

        to.messages_unread += 1
        to.put()

        logging.info("message '%s' sent to %s" % (subject, to.username))


def tweet(status):
    if not status or not status.strip() or len(status) < 5:
        return

    auth = tweepy.OAuthHandler(settings.TWITTER_OAUTH_CONSUMER_TOKEN, \
            settings.TWITTER_OAUTH_CONSUMER_SECRET)
    auth.set_access_token(settings.TWITTER_OAUTH_ACCESS_KEY, \
            settings.TWITTER_OAUTH_ACCESS_SECRET)
    api = tweepy.API(auth)
    api.update_status(status)
    logging.info("tweeted")


def shorturl(long_url):
    json_result = urlopen("http://api.bitly.com/v3/shorten?login=%s&apiKey=%s&longUrl=%s&format=json" % \
        (settings.BITLY_LOGIN, settings.BITLY_APIKEY, long_url)).read()
    r = json.loads(json_result)
    logging.info("bitly result: %s" % str(r))
    return r["data"]["url"]


def akismet_spamcheck(content, remote_addr, user_agent):
    """Returns True if spam, False if not spam"""
    try:
        real_key = akismet.verify_key(settings.AKISMET_APIKEY, \
            settings.AKISMET_URL)

        is_spam = akismet.comment_check(settings.AKISMET_APIKEY, \
            settings.AKISMET_URL, remote_addr, user_agent, \
            comment_content=content)

        if is_spam:
            return True
        else:
            return False

    except akismet.AkismetError, e:
        logging.error("%s, %s" % (e.response, e.statuscode))
