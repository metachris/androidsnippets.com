import os
import re
import logging
from operator import itemgetter

from google.appengine.api import memcache
from google.appengine.ext.webapp import template

from models import *

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


def tags_mostused(force_update=False):
    tags = memcache.get("tags_mostused")
    if tags and not force_update:
        return tags

    # Get all tags, build dict with key=name, val=snippet-count
    _tags = Tag.all()
    tags = {}
    for tag in _tags:
        cnt = tag.snippettag_set.count()
        tags[tag.name] = cnt

    # Now sort and take only top 50
    sorted_tags = sorted(tags.iteritems(), key=itemgetter(1), reverse=True)
    sorted_tags = sorted_tags[:100]

    memcache.set("tags_mostused", sorted_tags)
    return sorted_tags


def sitemap(force_update=False):
    sitemap = memcache.get("sitemap")
    if sitemap and not force_update:
        logging.info("returning cached sitemap")
        return sitemap

    logging.info("recreating sitemap")

    snippets = Snippet.all()
    snippets.order("-date_submitted")
    urls = []
    for snippet in snippets:
        urls.append({
            "loc": "http://www.androidsnippets.com/%s" % snippet.slug1,
            "lastmod": snippet.date_lastactivity,
            'priority': 0.9
        })
    logging.info("urls: %s" % len(urls))

    tags = Tag.all()
    tags.order("-date_added")
    for tag in tags:
        urls.append({
            "loc": "http://www.androidsnippets.com/tags/%s" % tag.name,
            "lastmod": tag.date_added,
            'priority': 0.7
        })
    logging.info("urls: %s" % len(urls))

    _users = InternalUser.all()
    #_users.order("-date_lastactivity")
    for user in _users:
        urls.append({
            "loc": "http://www.androidsnippets.com/users/%s" % user.nickname,
            "lastmod": user.date_lastactivity,
            'priority': 0.4
        })
    logging.info("urls: %s" % len(urls))

    out = template.render(tdir + "sitemap.xml", {"urls": urls})
    memcache.set("sitemap", out)
    return out
