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
from tools import slugify, decode, is_valid_email
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
        self.response.out.write(template.render(tdir + "user_profile.html", \
                values))


class ProfileView(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        values = {
            'prefs': prefs,
            'tab2': self.request.get('n') == '1',
            'error2': self.request.get('u') == '2'
        }
        self.response.out.write(template.render(tdir + "profile.html", values))

    def post(self):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        update = decode(self.request.get('update'))
        if update == "about":
            nickname = decode(self.request.get('nickname'))
            email = decode(self.request.get('email'))
            twitter = decode(self.request.get('twitter'))
            about = decode(self.request.get('about'))

            url_addon = ""
            if nickname and nickname != prefs.nickname and len(nickname) > 3:
                # check if nick is still available, if so then update
                q = UserPrefs.all()
                q.filter("nickname =", nickname)
                if q.count():
                    # already taken
                    url_addon += "&u=-1"
                else:
                    # free. if email, only own is allowed
                    if is_valid_email(nickname):
                        if nickname == prefs.email:
                            prefs.nickname = nickname
                            url_addon += "&u=1"
                        else:
                            # othre email not permitted
                            url_addon += "&u=2"
                    else:
                        prefs.nickname = nickname
                        url_addon += "&u=1"

            if email and email != prefs.email:
                # verify email
                url_addon += "&e=1"

            if twitter and twitter != prefs.twitter:
                prefs.twitter = twitter
                url_addon += "&t=1"

            if about and about != prefs.about:
                prefs.about = about
                url_addon += "&a=1"

            if url_addon:
                prefs.put()
                url_addon = "%s%s" % ("?x=1", url_addon)

            self.redirect("/profile%s" % url_addon)
            return

        if update == "notifications":
            # Currently only 4 notification settings. increase as necessary
            notifications = 0
            for i in xrange(4):
                s = decode(self.request.get('n%s' % i))
                # n1 = lowest bit, n2 next higher, ...
                notifications |= 1 << i if s else 0

            #logging.info("= n before: %s" % prefs.notifications)
            #logging.info("= n after: %s" % notifications)

            url_addon = ""
            if notifications != prefs.notifications:
                prefs.notifications = notifications
                url_addon = "%s%s" % ("&n=1", url_addon)

            if url_addon:
                prefs.put()
                url_addon = "%s%s" % ("?x=1", url_addon)

            self.redirect("/profile%s" % url_addon)
            return
