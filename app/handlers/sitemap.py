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

from django.utils import simplejson as json

import markdown
import mc

from libs import PyRSS2Gen

from models import *
from tools import slugify, decode

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


class SitemapView(webapp.RequestHandler):
    def get(self):
        force_update = decode(self.request.get('n'))
        self.response.out.write(mc.cache.sitemap(force_update))
