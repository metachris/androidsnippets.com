import os
import logging
import hashlib

from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import mail

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

from google.appengine.ext.webapp import template

import markdown
import akismet

from urllib import unquote
from time import sleep
from tools import slugify, decode, is_valid_email, send_message
from models import *

import settings

"""
All handlers related to user profiles (/author/<nickname>)
"""

tdir = os.path.join(os.path.dirname(__file__), '../templates/')


# Custom sites
class UserProfileView(webapp.RequestHandler):
    """View an user's public profile"""
    def get(self, nickname):
        memcache.incr("pv_otherprofile", initial_value=0)
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        nick = nickname.replace("index.html", "").strip("/")
        q = UserPrefs.all()
        q.filter("nickname =", unquote(nick))  # @ is %40
        profile = q.get()

        if not profile:
            self.error(404)
            return

        values = {'prefs': prefs, 'profile': profile}
        self.response.out.write(template.render(tdir + "user_profile.html", \
                values))


class ProfileView(webapp.RequestHandler):
    """Private profile"""
    def get(self):
        memcache.incr("pv_profile", initial_value=0)
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        send_message(prefs, 10, "test", "body")

        info = ""
        error = ""
        a = self.request.get('a')  # email verification link
        e = self.request.get('e')  # 1=email verification sent
        u = self.request.get('u')  # nickname updated
        if a:
            if a == prefs.email_new_code:
                # Email verification successful
                if not prefs.email:
                    # initial email verification gets rep points
                    prefs.points += 3
                prefs.email = prefs.email_new
                prefs.email_new = None
                prefs.email_new_code = None
                prefs.put()
                info = "Email address verified!"

                # Check if email matches orphaned legacy prefs
                if UserPrefs.all().filter("email =", prefs.email).count():
                    send_message(prefs, 10, "Email change matches orphaned \
                        prefs", "user prefs: %s" % prefs.key())
            else:
                error = "Not a valid activation code"
        elif e == "1":
            info = "Verification email sent"
        else:
            if u == "-1":
                error = "Username already taken"
            elif u == "1":
                info = "Username changed"

        # This user's edits on other snippets
        edits = prefs.snippetrevision_set
        edits.filter("initial_revision =", False)
        edits.order("-date_lastactivity")

        # This user's submissions
        snippets = prefs.snippet_set
        snippets.order("-date_lastactivity")

        values = {
            'prefs': prefs,
            'tab2': self.request.get('n') == '1',
            'error2': u == '2',
            'error': error,
            'info': info,
            'snippets': snippets,
            'edits': edits,
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

            if email and email.strip() != prefs.email_new:
                # updating email address
                if prefs.email_new and email.strip() == prefs.email:
                    # switching back to already verified mail is ok
                    prefs.email = email.strip()
                    prefs.email_new = None
                    prefs.email_new_code = None
                    url_addon += "&e=2"

                else:
                    # send verification mail
                    prefs.email_new = email.strip()
                    prefs.email_new_code = hashlib.sha1(\
                            os.urandom(64)).hexdigest()

                    body_text = template.render(tdir + \
                            "/email/verify_text.html", \
                            {'code': prefs.email_new_code, 'email': email})

                    #print "x"
                    #print body_text
                    #return
                    message = mail.EmailMessage()
                    message.sender = \
                        "Android Snippets <chris@androidsnippets.com>"
                    message.to = email
                    message.subject = "Android snippets email verification"
                    message.body = body_text
                    #message.html = email_body_html
                    message.send()

                    url_addon += "&e=1"

            if twitter and twitter != prefs.twitter:
                prefs.twitter = twitter
                url_addon += "&t=1"

            if about and about != prefs.about:
                prefs.about = about
                prefs.about_md = markdown.markdown(about).replace( \
                        "<a ", "<a target='_blank' ")
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


class AccountRecoveryView(webapp.RequestHandler):
    def get(self):
        memcache.incr("pv_accoutrecovery", initial_value=0)
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        values = {'prefs': prefs}
        self.response.out.write(template.render(tdir + \
                "account_recovery.html", values))
