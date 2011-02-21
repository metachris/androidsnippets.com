#!/usr/bin/env python

"""
Services that are accessible to admin only (eg. cron).
"""

from google.appengine.api import mail
from google.appengine.api import taskqueue
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from models import Emails
from handlers import *


class Cron1(webapp.RequestHandler):
    def get(self):
        """Cron job that queries the db and forks a worker for each entry"""


urls = [
    (r'/services/cron1', Cron1),
    (r'/services/cron1-worker1', Cron1_Worker1),
]

application = webapp.WSGIApplication(urls, debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
