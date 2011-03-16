import os
import re
import logging
from operator import itemgetter

from google.appengine.api import memcache
from google.appengine.ext.webapp import template

from models import *

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


def tags_dict(force_update=False):
    tags = memcache.get("tags_dict")
    if tags and not force_update:
        # logging.info("return cached tags_dict")
        return tags

    # Get all tags, build dict with key=name, val=snippet-count
    _tags = Tag.all()
    tags = {}
    for tag in _tags:
        cnt = tag.snippettag_set.count()
        tags[tag.name] = cnt

    memcache.set("tags_dict", tags)
    return tags


def tags_mostused(force_update=False):
    sorted_tags = memcache.get("tags_mostused")
    if sorted_tags and not force_update:
        return sorted_tags

    logging.info("recreating tags")

    tags = tags_dict(force_update)

    # Now sort and take only top 50
    sorted_tags = sorted(tags.iteritems(), key=itemgetter(1), reverse=True)
    sorted_tags = sorted_tags[:100]

    memcache.set("tags_mostused", sorted_tags)
    return sorted_tags


def sitemap(force_update=False):
    sitemap = memcache.get("sitemap")
    if sitemap and not force_update:
        # logging.info("returning cached sitemap")
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
    # logging.info("urls: %s" % len(urls))

    tags = Tag.all()
    tags.order("-date_added")
    for tag in tags:
        urls.append({
            "loc": "http://www.androidsnippets.com/tags/%s" % tag.name,
            "lastmod": tag.date_added,
            'priority': 0.7
        })
    # logging.info("urls: %s" % len(urls))

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

    # logging.info("adding comment, depth %s" % depth)
    html = template.render(tdir + "comment.html", {"comment": comment, \
            'depth': depth * 4})

    for c in comment.snippetcomment_set.order("date_submitted"):
        d = depth + 1
        html += snippet_comment_recursive(c, d)

    return html


def snippet_comments(snippet_key, force_update=False):
    html = memcache.get("comments_%s" % snippet_key)
    if html and not force_update:
        # logging.info("returning cached comments")
        return html if html != 1 else ""

    # Get snippet from db
    snippet = Snippet.get(snippet_key)
    if not snippet:
        return None

    logging.info("recreating comments [%s]" % snippet.slug1)

    # Recalculate comment tree. Start with parent comments only
    q = db.GqlQuery("SELECT * FROM SnippetComment WHERE snippet = :1 AND \
            parent_comment < '' AND flagged_as_spam = :2 \
            ORDER BY parent_comment ASC, flagged_as_spam ASC, \
            date_submitted ASC", snippet, False)

    html = u""
    for comment in q:
        html += snippet_comment_recursive(comment)

    memcache.set("comments_%s" % snippet_key, html if len(html) > 0 else 1)
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

    logging.info("rebuilding cached snippet list [%s]" % category)

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


def snippet(snippet_slug, force_update=False, clear=False):
    if clear:
        memcache.delete("snippet_%s" % snippet_slug)
        return

    _snippet = memcache.get("snippet_%s" % snippet_slug)
    if _snippet and not force_update:
        # logging.info("return cached snippet")
        return _snippet

    logging.info("recreate snippet")

    q = Snippet.all()
    q.filter("slug1 =", snippet_slug)
    snippet = q.get()
    if not snippet:
        return None

    _snippet = {
        'key': snippet.key(),
        "userprefs": snippet.userprefs,
        "slug1": snippet.slug1,
        "views": snippet.views,
        "date_lastactivity": snippet.date_lastactivity,
        "comment_count": snippet.comment_count,
        "upvote_count": snippet.upvote_count,
        "title": snippet.title,
        "description": snippet.description,
        "description_md": snippet.description_md,
        "code": snippet.code,
        "_tags": [],
        "tags": [],  # tuples with (tag, count) - completed in handler
    }

    for tag in snippet.snippettag_set:
        _snippet["_tags"].append(tag.tag.name)

    memcache.set("snippet_%s" % snippet_slug, _snippet)
    return _snippet


def has_upvoted(prefs, snippet_key, force_update=False, clear=False):
    if not prefs:
        #logging.info("x1")
        return False

    if clear:
        memcache.delete("snippet_upvote_%s_%s" % (prefs.key(), snippet_key))
        #x = memcache.get("snippet_upvote_%s_%s" % (prefs.key(), snippet_key))
        #logging.info("x2, %s" % prefs.key())
        #logging.info("x2,:%s" % x)
        return

    voted = memcache.get("snippet_upvote_%s_%s" % (prefs.key(), snippet_key))
    if voted and not force_update:
        # 'not voted' is memcached as -1
        #logging.info("x3, %s, %s" % (voted, prefs.key()))
        return True if voted > 0 else False

    logging.info("recreate has_upvoted")

    # Get snippet from db
    snippet = Snippet.get(snippet_key)
    if not snippet:
        return None

    # see if user has voted
    q1 = db.GqlQuery("SELECT * FROM SnippetUpvote WHERE \
            userprefs = :1 and snippet = :2", prefs, snippet)
    voted = q1.count()
    #logging.info("x voted count: %s" % voted)
    memcache.set("snippet_upvote_%s_%s" % (prefs.key(), snippet_key), \
            voted or -1)
    return voted


def snippets_related(cached_snippet, force_update=False, clear=False):
    """ Return list of related snippets to this one """
    tags = cached_snippet["_tags"]
