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

import mc
from libs import tweepy
from settings import *
from tools import tweet

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


# Custom sites
class AdminX(webapp.RequestHandler):
    def get(self, n):
        # each page adds 10 users
        page = int(n)


class AdminY(webapp.RequestHandler):
    def get(self, n):
        # each page adds 10 snippets
        page = int(n)


class AdminDel(webapp.RequestHandler):
    def get(self):
        pass


class AdminView(webapp.RequestHandler):
    def get(self, category=None):
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)
        values = {'prefs': prefs, "stats": []}

        mc_items = ["pv_login", "pv_main", "pv_profile", "pv_snippet", \
        "pv_snippet_legacy", "ua_vote_snippet", "ua_edit_snippet", \
        "pv_snippet_edit", "pv_tag", "ua_comment", "ua_comment_spam", \
        "ua_comment_ham", "pv_otherprofile", "pv_search", "pv_userlist", \
        "pv_snippet_404"]
        mc_items.sort()

        if not category:
            self.response.out.write( \
                    template.render(tdir + "admin.html", values))

        if category == "/stats":
            for item in mc_items:
                values["stats"].append((item, memcache.get(item)))
            self.response.out.write( \
                    template.render(tdir + "admin_stats.html", values))

        if category == "/stats/reset":
            for item in mc_items:
                memcache.set(item, 0)
            self.redirect("/admin/stats")

        if category == "/revision":
            key = decode(self.request.get('k'))
            action = decode(self.request.get('a'))
            if key:
                rev = SnippetRevision.get(db.Key(key))
                if rev:
                    if action == "1":
                        # use as default
                        rev.merge(prefs)
                    elif action == "2":
                        # delete revision
                        for v in rev.snippetrevisionupvote_set:
                            v.delete()
                        for v in rev.snippetrevisiondownvote_set:
                            v.delete()
                        rev.snippet.proposal_count -= 1
                        rev.snippet.put()
                        rev.delete()

                        self.redirect("/admin/revision")
                        return

                values["rev"] = rev
                self.response.out.write( \
                    template.render(tdir + "admin_rev.html", values))
            else:
                revs = SnippetRevision.all()
                revs.filter("merged =", False)
                revs.order("-date_submitted")
                values["revs"] = revs.fetch(40)
                self.response.out.write( \
                    template.render(tdir + "admin_revlist.html", values))


# Custom sites
class AdminSnippetView(webapp.RequestHandler):
    def get(self, snippet_key):
        # each page adds 10 users
        snippet = Snippet.get(db.Key(snippet_key))
        if not snippet:
            self.error(404)
            return

        d = self.request.get('del')
        if d == "1":
            q = SnippetComment.all()
            q.filter("snippet =", snippet)
            for c in q:
                c.delete()

            q = SnippetUpvote.all()
            q.filter("snippet =", snippet)
            for c in q:
                c.delete()

            q = SnippetTag.all()
            q.filter("snippet =", snippet)
            for c in q:
                c.delete()

            q = SnippetRevision.all()
            q.filter("snippet =", snippet)
            for c in q:
                # for each revision, also delete up and downvotes
                q2 = SnippetRevisionUpvote.all()
                q2.filter("snippetrevision =", c)
                for c2 in q2:
                    c2.delete()

                q2 = SnippetRevisionDownvote.all()
                q2.filter("snippetrevision =", c)
                for c2 in q2:
                    c2.delete()

                # after deleting votes, delete revision
                c.delete()

            # Reduce the reputation points from the user by number of votes
            snippet.userprefs.points -= snippet.upvote_count
            snippet.userprefs.put()

            # finally delete the snippet
            snippet.delete()

            print "deleted"
            return

        html = """Snippet: %s<br><br><a href="?del=1">delete</a> <a href=
        "https://appengine.google.com/datastore/edit?app_id=android-snippets&namespace=&key=%s"
        target="_blank">edit</a>
        """ % (snippet.title, snippet.key())
        self.response.out.write(html)


# Custom sites
class AdminCommentView(webapp.RequestHandler):
    def get(self, comment_key):
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)

        comment = SnippetComment.get(db.Key(comment_key))
        if not comment:
            self.error(404)
            return

        values = {'prefs': prefs, 'comment': comment}
        self.response.out.write( \
            template.render(tdir + "admin/comment.html", values))

    def post(self, comment_key):
        comment = SnippetComment.get(db.Key(comment_key))
        if not comment:
            self.error(404)
            return

        msg = decode(self.request.get('msg'))
        update = decode(self.request.get('update'))
        delete = decode(self.request.get('delete'))

        if update:
            comment.comment = msg
            comment.comment_md = markdown.markdown(msg.replace( \
                "<a ", "<a target='_blank' rel='nofollow' "))
            comment.put()
            logging.info("comment updated by admin")

            # Update cached comments
            mc.cache.snippet_comments(comment.snippet.key(), True)
            mc.cache.snippet(snippet.slug1, force_update=True)

            self.redirect("/admin/comment/%s" % comment_key)

        elif delete:
            redirect_to = "/%s" % comment.snippet.slug1
            snippet = comment.snippet
            comment.delete()

            # Update snippet's date_lastcomment
            comments = snippet.snippetcomment_set.order("-date_submitted")
            comment_last = comments.fetch(1)
            if not comment_last:
                snippet.date_lastcomment = None
            else:
                snippet.date_lastcomment = comment_last[0].date_submitted

            # Update snippet's comment count
            snippet.comment_count -= 1
            snippet.put()

            mc.cache.snippet_comments(snippet.key(), force_update=True)
            mc.cache.snippet(snippet.slug1, force_update=True)

            logging.info("comment deleted by admin")
            self.redirect(redirect_to)
