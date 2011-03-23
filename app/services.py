"""
Services that are accessible to admin only (eg. cron).
"""
import logging
import time

from google.appengine.api import mail
from google.appengine.api import taskqueue

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import mc

from handlers import *


class UpdateTags(webapp.RequestHandler):
    def get(self):
        """Updates tags for mc after adding a snippet (db intensive)"""
        logging.info("service: tag update started")
        t1 = time.time()
        mc.cache.tags_mostused(force_update=True)
        logging.info("service: tag update took %s s" % (time.time() - t1))
        return

    def post(self):
        self.get()


class UpdateSitemap(webapp.RequestHandler):
    def post(self):
        self.get()

    def get(self):
        """Updates tags for mc after adding a snippet (db intensive)"""
        logging.info("service: sitemap update started")
        t1 = time.time()
        mc.cache.sitemap(force_update=True)
        logging.info("service: sitemap update took %s s" % (time.time() - t1))
        return


class UpdateRelations(webapp.RequestHandler):
    def post(self):
        self.get()

    def get(self):
        mc.cache.snippets_build_relations(memcache_snippets=False)


urls = [
    (r'/services/update_tags', UpdateTags),
    (r'/services/update_sitemap', UpdateSitemap),
    (r'/services/update_relations', UpdateRelations),
]

application = webapp.WSGIApplication(urls, debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
