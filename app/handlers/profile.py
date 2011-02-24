import os
import logging

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

from google.appengine.ext.webapp import template

import markdown
import akismet

from urllib import unquote
from time import sleep
from tools import slugify, decode
from models import *

import settings

"""
All handlers related to user profiles (/author/<nickname>)
"""

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


# Custom sites
class UserProfileView(webapp.RequestHandler):
    def get(self, nickname):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        q = UserPrefs.all()
        q.filter("nickname =", unquote(nickname))  # @ is %40
        profile = q.get()

        values = {'prefs': prefs, 'profile': profile}
        self.response.out.write(template.render(tdir + "profile.html", values))
