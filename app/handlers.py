import os

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from models import *

# Setup jinja templating
template_dirs = []
template_dirs.append(os.path.join(os.path.dirname(__file__), 'templates'))
env = Environment(loader=FileSystemLoader(template_dirs))


# OpenID Login
class LogIn(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        action = self.request.get('action')
        target_url = self.request.get('continue')
        if action and action == "verify":
            f = self.request.get('openid_identifier')
            url = users.create_login_url(target_url, federated_identity=f)
            self.redirect(url)
        else:
            html = env.get_template('login.html').render()
            self.response.out.write(html)


class LogOut(webapp.RequestHandler):
    def get(self):
        url = users.create_logout_url("/")
        self.redirect(url)


# Custom sites
class Main(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        values = {'user': user, 'prefs': prefs}
        html = env.get_template('index.html').render(values)
        self.response.out.write(html)


class Account(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        html = env.get_template('index.html').render({'user': user})
        self.response.out.write(html)


# @login_required only works on get, now handled via app.yaml
class SnippetsNew(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        html = env.get_template('snippets_new.html').render({'user': user})
        self.response.out.write(html)

    def post(self):
        """Check and add new snippet to db"""
        user = users.get_current_user()

        # Validate input
        title = self.request.get('title')
        code = self.request.get('code')
        description = self.request.get('description')

        if not title or not code or not description:
            values = {'user': user, 'prefs': prefs, 'errors': True}
            html = env.get_template('snippets_new.html').render(values)
            self.response.out.write(html)
            return

        # Create snippet
        s = Snippet(submitter=user)
        s.save()

        # Create the first upvote
        u = SnippetUpvote(user=user, snippet=s)
        u.save()

        # Create initial revision
        r = SnippetRevision(snippet=s, contributor=user)
        r.approved = True
        r.approved_by = user
        r.title = title
        r.description = description
        r.code = code
        r.save()
        print r

        # Redirect to snippet view


class SnippetView(webapp.RequestHandler):
    def get(self, snippet_id):
        print "view snippet %s" % snippet_id
        return
        user = users.get_current_user()
        html = env.get_template('snippet_view.html').render({'user': user})
        self.response.out.write(html)
