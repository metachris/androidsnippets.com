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
from tools import slugify
from django.utils import simplejson as json
import markdown

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


# Custom sites
class AdminX(webapp.RequestHandler):
    def get(self, n):
        # each page adds 10 snippets
        page = int(n)

        f = open("snippets.json")
        s = f.read()
        f.close()

        snippets = json.loads(s)
        for _s in snippets[page * 10:(page + 1) * 10]:
            # 1. find corresponding user
            # 2. add snippet
            # 3. add revision
            # 4. add tags

            q = UserPrefs.all()
            q.filter("legacy_user_id =", int(_s[5]))
            prefs = q.get()

            logging.info("prefs for id %s: %s" % (_s[5], prefs))
            if not prefs:
                logging.info("didnt find prefs, using chris")
                q = UserPrefs.all()
                q.filter("nickname =", "metakaram")
                prefs = q.get()

            #"id";"title";"desc";"code";"pub_date";"author_id";"tags";"views"
            # Find a free slug
            title = _s[1]
            slug = slugify(title)
            _slug = slugify(title)
            cnt = 0
            while True:
                q = Snippet.all()
                q.filter("slug1 =", _slug)
                if q.count() > 0:
                    cnt += 1
                    _slug = u"%s%s" % (slug, cnt + 1)
                else:
                    slug = _slug
                    break

            s = Snippet(userprefs=prefs)
            s.title = _s[1]
            s.slug1 = slug
            s.description = _s[2]
            s.description_md = markdown.markdown(_s[2]).replace(
                "<a ", "<a target='_blank' ")
            s.code = _s[3]
            s.android_minsdk = 3
            s.views = int(_s[7])
            s.slug2 = _s[0]
            s.put()

            # Create the first revision
            r = SnippetRevision.create_first_revision(userprefs=prefs, \
                    snippet=s)
            r.put()

            # Create the tags
            tags = _s[6].split(" ")
            for tag in tags:
                if not tag or len(tag.strip()) < 3:
                    # skip empty and too short tags
                    continue

                tag = tag.strip(",")

                # See if tag base object already exists, if not then create it
                q = Tag.all()
                q.filter("name =", tag)
                t = q.get()
                if not t:
                    t = Tag(name=tag)
                    t.put()

                st = SnippetTag(snippet=s, tag=t)
                st.put()


class AdminY(webapp.RequestHandler):
    def get(self, email=None):
        if email:
            q = UserPrefs.all()
            q.filter("email =", unquote(email))
            self.response.out.write(", %s: %s" % (email, q.count()))


class AdminDel(webapp.RequestHandler):
    def get(self):
        q = Snippet.all()
        for p in q:
            p.delete()
        q = SnippetRevision.all()
        for p in q:
            p.delete()
        q = SnippetTag.all()
        for p in q:
            p.delete()
        q = Tag.all()
        for p in q:
            p.delete()


class AdminView(webapp.RequestHandler):
    def get(self, category=None):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)
        values = {'prefs': prefs, "stats": []}

        mc_items = ["pv_login", "pv_main", "pv_profile", "pv_snippet", \
        "pv_snippet_legacy", "ua_vote_snippet", "ua_edit_snippet", \
        "pv_snippet_edit", "pv_tag", "ua_comment", "ua_comment_spam", \
        "ua_comment_ham", "pv_otherprofile"]
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
