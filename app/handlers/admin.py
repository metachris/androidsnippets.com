import os
import logging
import time
import datetime
from urllib import unquote

from google.appengine.ext import db
from google.appengine.api import users
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
