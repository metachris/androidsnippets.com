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

    """
    _users = InternalUser.all()
    #_users.order("-date_lastactivity")
    for user in _users:
        urls.append({
            "loc": "http://www.androidsnippets.com/users/%s" % user.nickname,
            "lastmod": user.date_lastactivity,
            'priority': 0.4
        })
    logging.info("urls: %s" % len(urls))
    """

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
        #logging.info("returning cached comments")
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


def snippet_list(category, page=1, items=20, force_update=False, clear=False):
    """Cache of the snippet objects for the listings"""
    if clear:
        if category:
            cats = [category]
        else:
            cats = ["/new", "/active", "/popular", "/comments", "/edits"]
        for cat in cats:
            memcache.delete("snippets_p%s_%s" % (page, cat))
        return

    snippets = memcache.get("snippets_p%s_%s" % (page, category))
    if snippets and not force_update:
        return snippets

    logging.info("rebuilding cached snippets")

    q = Snippet.all()
    if category == "/new":
        q.order("-date_submitted")
    elif category == "/active":
        q.order("-date_lastactivity")
    elif category == "/popular":
        q.order("-upvote_count")
    elif category == "/comments":
        q.filter("date_lastcomment !=", None)
        q.order("-date_lastcomment")
    elif category == "/edits":
        q.filter("proposal_count >", 0)
        q.order("proposal_count")

    _snippets = q.fetch(items, items * (page - 1))

    snippets = []
    for s in _snippets:
        snippets.append({
            'title': s.title,
            'slug1': s.slug1,
            'upvote_count': s.upvote_count,
            'comment_count': s.comment_count,
            'date_lastactivity': s.date_lastactivity,
            'nickname': s.userprefs.nickname,
            'tags': [tag.tag.name for tag in s.snippettag_set]
        })

    memcache.set("snippets_p%s_%s" % (page, category), snippets)
    return snippets
