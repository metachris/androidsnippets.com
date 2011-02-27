import os
import logging
import time
import datetime
from urllib import unquote

from google.appengine.api import users
from google.appengine.api import memcache

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

from models import *
from tools import slugify, decode
from django.utils import simplejson as json

import markdown
from libs import PyRSS2Gen

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


class StringFile:
    s = ""

    def write(self, x):
        self.s += x

    def get(self):
        return self.s


class FeedView(webapp.RequestHandler):
    def get(self, category):
        if category.strip("/") == "latest":
            items = []
            s = Snippet.all()
            s.order("-date_submitted")
            snippets = s.fetch(30)
            for snippet in snippets:
                items.append(PyRSS2Gen.RSSItem(title="%s" % snippet.title,
                    link="http://www.androidsnippets.com/%s" % snippet.slug1,
                    description=snippet.description_md,
                    guid=PyRSS2Gen.Guid("http://www.androidsnippets.com/%s" \
                            % snippet.slug1),
                    pubDate=datetime.datetime(2003, 9, 6, 21, 31)
                ))

            rss = PyRSS2Gen.RSS2(
                title="Android Snippets - Latest Snippets",
                link="http://www.androidsnippets.com",
                description="AndroidSnippets is a community driven website \
                    for finding, exploring, sharing and improving source code \
                    snippets for Android.",
                lastBuildDate=datetime.datetime.utcnow(),
                items=items)

            o = StringFile()  # instead of writing to file, we use this str
            rss.write_xml(o)
            self.response.out.write(o.get())

        if category.strip("/") == "comments":
            items = []
            q = SnippetComment.all()
            q.filter("flagged_as_spam =", False)
            q.order("-date_submitted")
            comments = q.fetch(30)
            for comment in comments:
                items.append(PyRSS2Gen.RSSItem(
                    title="%s" % comment.snippet.title,
                    link="http://www.androidsnippets.com/%s" % \
                            comment.snippet.slug1,
                    description=comment.snippet.description_md,
                    guid=PyRSS2Gen.Guid("http://www.androidsnippets.com/%s" \
                            % comment.snippet.slug1),
                    pubDate=datetime.datetime(2003, 9, 6, 21, 31)
                ))

            rss = PyRSS2Gen.RSS2(
                title="Android Snippets - Latest Comments",
                link="http://www.androidsnippets.com",
                description="AndroidSnippets is a community driven website \
                    for finding, exploring, sharing and improving source code \
                    snippets for Android.",
                lastBuildDate=datetime.datetime.utcnow(),
                items=items)

            o = StringFile()  # instead of writing to file, we use this str
            rss.write_xml(o)
            self.response.out.write(o.get())

        else:
            self.error(404)
