import os
import logging
import time
import datetime

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
    def get(self):
        f = open("users.json")
        s = f.read()
        f.close()
        print "load old user db"
        users = json.loads(s)
        print len(users)
        #for user in users:
        #    _d = time.strptime(user[2], "%Y-%m-%d %H:%M:%S")
        #    d = datetime.datetime(*d[:6])
        #    prefs = UserPrefs.from_data(user[0], user[1], d)
