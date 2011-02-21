import os
import logging

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

#from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from google.appengine.ext.webapp import template

import markdown

from urllib import unquote
from time import sleep
from tools import slugify, decode
from models import *

# Setup jinja templating
tdir = os.path.join(os.path.dirname(__file__), '../templates/')
#env = Environment(loader=FileSystemLoader(template_dirs))


# @login_required only works on get, now handled via app.yaml
class SnippetsNew(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)
        self.response.out.write(template.render(tdir + \
            "snippets_new.html", {'prefs': prefs, 'tag_cnt': 0}))

    def post(self):
        """Check and add new snippet to db"""
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        # Validate input
        title = self.request.get('title')
        code = self.request.get('code')
        description = self.request.get('description')

        tags = []
        i = 0
        while True:
            tag = self.request.get('tag%s' % i)
            logging.info("tag: %s" % tag)
            if not tag:
                break
            elif tag == "0":
                # placeholder for removed tag
                pass
            else:
                tags.append(decode(tag))
            i += 1

        errors = []
        if not title:
            errors.append("title")
        if not code:
            errors.append("snippet")
        if not description:
            errors.append("description")
        if len(tags) < 2:
            errors.append("a few tags")
        if len(errors) > 0:
            values = {'prefs': prefs, 'errors': errors, 'title': title, \
                'code': code, 'description': description, 'tags': tags, \
                'tag_cnt': len(tags)}
            self.response.out.write(template.render(tdir + \
                "snippets_new.html", values))
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

        # Create the tags
        for tag in tags:
            if not tag or len(tag.strip()) < 4:
                # skip empty and too short tags
                continue

            # See if tag base object already exists, if not then create it
            q = Tag.all()
            q.filter("name =", tag)
            t = q.get()
            if not t:
                t = Tag(name=tag)
                t.put()

            st = SnippetTag(snippet=s, tag=t)
            st.put()

        # Redirect to snippet view
        self.redirect("/%s" % s.slug1)


class SnippetsNewPreview(webapp.RequestHandler):
    """Popup that shows an edit from another user"""
    def get(self):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        title = unquote(decode(self.request.get('title')))
        code = unquote(decode(self.request.get('code')))
        description = decode(self.request.get('desc'))
        desc_md = markdown.markdown(unquote(description))
        tags = decode(self.request.get('tags'))

        values = {"prefs": prefs, "title": title, "code": code, 'desc_md': \
                desc_md, 'tags': tags, 'preview': True}
        self.response.out.write(template.render(tdir + \
            "snippets_edit_view.html", values))

    def post(self):
        return self.get()
