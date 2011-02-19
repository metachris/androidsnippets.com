import os
import logging

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

#from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from google.appengine.ext.webapp import template

from time import sleep
from tools import slugify, decode
from models import *

# Setup jinja templating
tdir = os.path.join(os.path.dirname(__file__), 'templates/')
#env = Environment(loader=FileSystemLoader(template_dirs))


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
            self.response.out.write(template.render(tdir + "login.html", \
                    {"continue_to": target_url}))


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

        values = {'prefs': prefs, 'snippets': snippets}
        self.response.out.write(template.render(tdir + "index.html", values))


class Account(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()


# @login_required only works on get, now handled via app.yaml
class SnippetsNew(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)
        self.response.out.write(template.render(tdir + \
            "snippets_new.html", {'prefs': prefs}))

    def post(self):
        """Check and add new snippet to db"""
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        # Validate input
        title = self.request.get('title')
        code = self.request.get('code')
        description = self.request.get('description')
        tags = self.request.get('tags')

        errors = []
        if not title:
            errors.append("title")
        if not code:
            errors.append("snippet")
        if not description:
            errors.append("description")
        if not tags:
            errors.append("tags")
        if len(errors) > 0:
            values = {'prefs': prefs, 'errors': errors, 'title': title, \
                'code': code, 'description': description}
            self.response.out.write(template.render(tdir + \
                "snippets_new.html", values))
            return

        # Decode with utf-8 if necessary
        title = decode(title.strip())
        code = decode(code)
        description = decode(description)
        tags = decode(tags)

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

        # Create snippet (submitter is saved only in first revision)
        s = Snippet(userprefs=prefs)
        s.title = title
        s.slug1 = slug
        s.description = description
        s.code = code
        s.put()

        # Create the first revision
        r = SnippetRevision.create_first_revision(userprefs=prefs, snippet=s)
        r.put()

        # Create the first upvote
        upvote = SnippetUpvote(userprefs=prefs, snippet=s)
        upvote.put()

        # Redirect to snippet view
        self.redirect("/%s" % s.slug1)


class LegacySnippetView(webapp.RequestHandler):
    def get(self, legacy_slug):
        q = Snippet.all()
        q.filter("slug2 =", legacy_slug)
        snippet = q.get()

        if not snippet:
            # Show snippet-not-found.html
            user = users.get_current_user()
            prefs = UserPrefs.from_user(user)

            values = {'prefs': prefs}
            self.response.out.write(template.render(tdir + \
                "snippets_notfound.html", values))
            return

        self.redirect("/%s" % snippet.slug1, permanent=True)


class SnippetView(webapp.RequestHandler):
    def get(self, snippet_slug):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

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
            values = {'prefs': prefs, "q": snippet_slug}
            self.response.out.write(template.render(tdir + \
                "snippets_notfound.html", values))
            return

        values = {'prefs': prefs, "prefs": prefs, "snippet": snippet}
        self.response.out.write(template.render(tdir + \
            "snippets_view.html", values))


class SnippetVote(webapp.RequestHandler):
    def get(self, snippet_slug):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        if not user:
            self.response.out.write("-1")
            return

        q = Snippet.all()
        q.filter("slug1 =", snippet_slug)
        snippet = q.get()

        if not snippet:
            self.error(404)

        else:
            # Check if user has already voted
            q = SnippetUpvote.all()
            q.filter("userprefs = ", prefs)
            q.filter("snippet =", snippet)
            vote = q.get()

            if vote:
                # Has already voted
                self.response.out.write("0")
            else:
                # Create the upvote
                u = SnippetUpvote(userprefs=prefs, snippet=snippet)
                u.save()
                snippet.upvote()
                snippet.save()
                self.response.out.write("1")


class SnippetEdit(webapp.RequestHandler):
    """TODO: Check if all form input is here, if user is allowed, etc"""
    def post(self, snippet_slug):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        title = decode(self.request.get('title'))
        code = decode(self.request.get('code'))
        description = decode(self.request.get('description'))
        tags = decode(self.request.get('tags'))

        if not title or not code or not description:
            self.response.out.write("-1")
            return

        q = Snippet.all()
        q.filter("slug1 =", snippet_slug)
        snippet = q.get()

        if not snippet:
            self.error(404)
            return

        # Create a new revision
        r = SnippetRevision(userprefs=prefs, snippet=snippet)
        r.title = title
        r.description = description
        r.code = code
        r.put()

        if user == snippet.userprefs.user:
            # Auto-merge new revision if edit by author
            r.merge(merged_by=prefs)
            self.response.out.write("0")
        else:
            # Add proposal info if from another editor
            snippet.proposal_count += 1
            snippet.date_lastproposal = datetime.datetime.now()
            snippet.date_lastactivity = datetime.datetime.now()
            self.response.out.write("1")
