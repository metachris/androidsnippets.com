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

from libs import tweepy
from settings import *
from tools import tweet

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


# Custom sites
class AdminX(webapp.RequestHandler):
    def get(self, n):
        # each page adds 10 users
        page = int(n)

        f = open("comments.json")
        s = f.read()
        f.close()

        comments = json.loads(s)
        for cols in comments[page * 50:(page + 1) * 50]:
            # see if user is registered
            #cols = ["id", "snippet_legacy_id", "user_legacy_id", "user_name",
            #        "user_email", "user_url", "comment", "submit_date"]
            snippet = Snippet.all().filter("slug2 =", str(cols[1])).get()
            if not snippet:
                logging.error("snippet %s not found" % cols[1])
                continue

            prefs = None
            if cols[2]:
                # see if we have legacy user
                prefs = InternalUser.all().filter("legacy_user_id =", \
                        cols[2]).get()

            if not prefs:
                #logging.info("create orphaned prefs entity")
                prefs = InternalUser.from_data(cols[3], cols[4], \
                        datetime.datetime.now())

            c = SnippetComment(userprefs=prefs, snippet=snippet, \
                comment=cols[6], \
                date_submitted=datetime.datetime.fromtimestamp(cols[7]),
                date_lastupdate=datetime.datetime.fromtimestamp(cols[7])
            )

            #logging.info(c.date_lastupdate)
            c.comment_md = markdown.markdown(cols[6]).replace( \
                "<a ", "<a target='_blank' rel='nofollow' ")
            c.save()

            snippet.comment_count += 1
            snippet.put()
            #logging.info("comment saved")


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
