import os

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from tools import slugify, decode
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

        q = Snippet.all()
        q.order("-date_submitted")
        snippets = q.fetch(20)

        values = {'user': user, 'prefs': prefs, 'snippets': snippets}
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

        # Decode with utf-8 if necessary
        title = decode(title.strip())
        code = decode(code)
        description = decode(description)

        # Find a free slug
        slug = slugify(title)
        _slug = slugify(title)
        cnt = 0
        while True:
            q = Snippet.all()
            q.filter("slug1 =", _slug)
            if q.count() > 0:
                cnt += 1
                _slug = u"%s%s" % (slug, cnt + 1)
            else:
                slug = _slug
                break

        # Create snippet
        s = Snippet(submitter=user)
        s.title = title
        s.slug1 = slug
        s.description = description
        s.code = code
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

        # Redirect to snippet view
        self.redirect("/snippets/%s" % s.slug1)


class SnippetView(webapp.RequestHandler):
    def get(self, snippet_slug):
        user = users.get_current_user()

        q = Snippet.all()
        q.filter("slug1 =", snippet_slug)
        snippet = q.get()

        if not snippet:
            # Support legacy system with old id's
            q = Snippet.all()
            q.filter("slug2 =", snippet_slug)
            snippet = q.get()

        if not snippet:
            # Show snippet-not-found.html
            values = {'user': user, "q": snippet_slug}
            html = env.get_template('snippets_notfound.html').render(values)
            self.response.out.write(html)
            return

        values = {'user': user, "snippet": snippet}
        html = env.get_template('snippets_view.html').render(values)
        self.response.out.write(html)
