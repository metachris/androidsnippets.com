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
        cnt = 0
        _d = time.strptime(user[2], "%Y-%m-%d %H:%M:%S")
        d = datetime.datetime(*_d[:6])


class AdminY(webapp.RequestHandler):
    def get(self, email=None):
        if email:
            q = UserPrefs.all()
            q.filter("email =", unquote(email))
            self.response.out.write(", %s: %s" % (email, q.count()))
