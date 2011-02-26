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

from django.utils import simplejson as json

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


# Custom sites
class AdminX(webapp.RequestHandler):
    def get(self, n):
        # each page adds 100 users
        page = int(n)

        f = open("users.json")
        s = f.read()
        f.close()

        _users = json.loads(s)
        for user in _users[page * 100:(page + 1) * 100]:
            _d = time.strptime(user[3], "%Y-%m-%d %H:%M:%S")
            d = datetime.datetime(*_d[:6])
            if user[3] == "NULL":
                user[3] = None
            UserPrefs.from_data(user[1], user[2], d, user[4], int(user[0]))


class AdminY(webapp.RequestHandler):
    def get(self, email=None):
        if email:
            q = UserPrefs.all()
            q.filter("email =", unquote(email))
            self.response.out.write(", %s: %s" % (email, q.count()))


class AdminDel(webapp.RequestHandler):
    def get(self):
        q = UserPrefs.all()
        for p in q:
            p.delete()


class AdminView(webapp.RequestHandler):
    def get(self, category=None):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)
        values = {'prefs': prefs, "stats": []}

        if not category:
            self.response.out.write( \
                    template.render(tdir + "admin.html", values))

        if category == "/stats":
            mc_items = ["pv_login", "pv_main", "pv_profile", "pv_snippet", \
            "pv_snippet_legacy", "ua_vote_snippet", "ua_edit_snippet", \
            "pv_snippet_edit", "pv_tag", "ua_comment", "ua_comment_spam", \
            "ua_comment_ham", "pv_otherprofile"]
            mc_items.sort()
            for item in mc_items:
                values["stats"].append((item, memcache.get(item)))
            self.response.out.write( \
                    template.render(tdir + "admin_stats.html", values))
