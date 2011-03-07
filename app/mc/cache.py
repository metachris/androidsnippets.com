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


def snippet_comment_recursive(comment, depth=0):
    """Starts with one parent comment and recursively
    builds the html for all children"""
    if not comment:
        return ""

    logging.info("adding comment, depth %s" % depth)
    html = template.render(tdir + "comment.html", {"comment": comment, \
            'depth': depth * 4})

    for c in comment.snippetcomment_set.order("date_submitted"):
        d = depth + 1
        html += snippet_comment_recursive(c, d)

    return html


def snippet_comments(snippet, force_update=False):
    html = memcache.get("comments_%s" % snippet.key())
    if html and not force_update:
        logging.info("returning cached comments")
        return html

    # Recalculate comment tree. Start with parent comments only
    q = db.GqlQuery("SELECT * FROM SnippetComment WHERE snippet = :1 AND \
            parent_comment < '' AND flagged_as_spam = :2 \
            ORDER BY parent_comment ASC, flagged_as_spam ASC, \
            date_submitted ASC", snippet, False)

    html = u""
    for comment in q:
        html += snippet_comment_recursive(comment)

    memcache.set("comments_%s" % snippet.key(), html)
    return html
