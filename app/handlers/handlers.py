import os
import logging
import datetime

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

import mc
from time import sleep
from tools import slugify, decode
from models import *

import settings

# Setup jinja templating
tdir = os.path.join(os.path.dirname(__file__), '../templates/')
#env = Environment(loader=FileSystemLoader(template_dirs))


# OpenID Login
class LogIn(webapp.RequestHandler):
    def get(self):
        memcache.incr("pv_login", initial_value=0)
        #user = users.get_current_user()
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


# Main snippet view sites
class Main(webapp.RequestHandler):
    def get(self, category=None):
        if not category or category == "/":
            category = "/active"

        memcache.incr("pv_main", initial_value=0)
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)

        p = decode(self.request.get('p'))
        page = int(p) if p else 1
        items_per_page = 20

        q = Snippet.all()
        if category == "/new":
            q.order("-date_submitted")
            title = "New Snippets"
        elif category == "/active":
            q.order("-date_lastactivity")
            title = "Active Snippets"
        elif category == "/popular":
            q.order("-upvote_count")
            title = "Popular Snippets"
        elif category == "/comments":
            q.filter("comment_count >", 0)
            q.order("-comment_count")
            title = "Recently Commented Snippets"
        elif category == "/edits":
            q.filter("proposal_count >", 0)
            q.order("proposal_count")
            title = "Snippets with Edits"
        snippets = q.fetch(items_per_page, items_per_page * (page - 1))
        values = {'prefs': prefs, 'snippets': snippets, 'title': title, \
                'page': page, 'pages': range(1, page)}
        self.response.out.write(template.render(tdir + \
                "snippet_list.html", values))
        return


class LegacySnippetView(webapp.RequestHandler):
    """Redirects for snippets of legacy androidsnippets.org, which have
    links such as http://androidsnippets.org/snippets/198

    Also handles /snippets/new, /snippets/active, etc.
    """
    def get(self, legacy_slug):
        memcache.incr("pv_snippet_legacy", initial_value=0)
        legacy_slug = legacy_slug.replace("index.html", "").strip("/")
        q = Snippet.all()
        q.filter("slug2 =", legacy_slug)
        snippet = q.get()

        if not snippet:
            # Show snippet-not-found.html
            user = users.get_current_user()
            prefs = InternalUser.from_user(user)

            values = {'prefs': prefs}
            self.response.out.write(template.render(tdir + \
                    "snippets_notfound.html", values))
            return

        self.redirect("http://www.androidsnippets.com/%s" % \
                snippet.slug1, permanent=True)


class SnippetDownloadView(webapp.RequestHandler):
    def get(self, snippet_slug):
        q = Snippet.all()
        q.filter("slug1 =", snippet_slug)
        snippet = q.get()

        if not snippet:
            # Show snippet-not-found.html
            values = {'prefs': prefs, "q": snippet_slug}
            self.response.out.write(template.render(tdir + \
                "snippets_notfound.html", values))
            return

        self.response.headers['Content-Type'] = "application/octet-stream"
        self.response.headers['content-disposition'] = \
                "attachment; filename=%s.java" % snippet.slug1
        self.response.out.write("%s\n// see http://androidsnippets.com/%s" % \
                (snippet.code, snippet.slug1))


class SnippetView(webapp.RequestHandler):
    def get(self, snippet_slug):
        memcache.incr("pv_snippet", initial_value=0)
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)

        q = Snippet.all()
        q.filter("slug1 =", snippet_slug)
        snippet = q.get()

        if not snippet:
            memcache.incr("pv_snippet_404", initial_value=0)
            logging.info("404: %s" % snippet_slug)
            # Show snippet-not-found.html
            values = {'prefs': prefs, "q": snippet_slug}
            self.response.out.write(template.render(tdir + \
                "snippets_notfound.html", values))
            return

        # Todo: temporarily store in memcache, update with cron
        snippet.views += 1
        snippet.save()

        # get all open revisions
        revisions = SnippetRevision.all()
        revisions.filter("snippet =", snippet)
        revisions.filter("merged =", False)
        revisions.filter("rejected =", False)
        revisions.order("-date_submitted")

        # but only include merged edits
        accepted_revisions = SnippetRevision.all()
        accepted_revisions.filter("snippet =", snippet)
        accepted_revisions.filter("merged =", True)
        accepted_revisions.order("date_submitted")

        # if commented and was marked as spam:
        commentspam = decode(self.request.get('c')) == "m"

        has_voted = False
        # see if user has voted
        if user:
            q1 = db.GqlQuery("SELECT * FROM SnippetUpvote WHERE \
                    userprefs = :1 and snippet = :2", prefs, snippet)
            q2 = db.GqlQuery("SELECT * FROM SnippetDownvote WHERE \
                    userprefs = :1 and snippet = :2", prefs, snippet)
            has_voted = q1.count() or -q2.count()  # 0 if not, 1, -1

        comments = snippet.snippetcomment_set.filter("flagged_as_spam =", \
                False)
        comments_html = template.render(tdir + "comments.html", \
                {"comments": comments, 'prefs': prefs})

        values = {"prefs": prefs, "snippet": snippet, "revisions": revisions, \
                'voted': has_voted, 'accepted_revisions': accepted_revisions, \
                "openedit": self.request.get('edit'), \
                "comments": comments, "comments_html": comments_html, \
                'commentspam': commentspam}

        self.response.out.write(template.render(tdir + \
            "snippets_view.html", values))


class SnippetVote(webapp.RequestHandler):
    def get(self, snippet_slug):
        memcache.incr("ua_vote_snippet", initial_value=0)
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)

        if not user:
            self.redirect("/%s" % snippet_slug)
            return

        q = Snippet.all()
        q.filter("slug1 =", snippet_slug)
        snippet = q.get()

        if not snippet:
            self.error(404)
            return

        # Check if user has already voted
        q = SnippetUpvote.all()
        q.filter("userprefs = ", prefs)
        q.filter("snippet =", snippet)
        vote = q.get()

        if not vote:
            # Has not already voted, create the upvote now
            u = SnippetUpvote(userprefs=prefs, snippet=snippet)
            u.save()
            snippet.upvote()
            snippet.save()

            # +1 rep point for author and all authors of merged edits
            for revision in snippet.snippetrevision_set:
                if revision.merged:
                    # if the user which votes is an author of an edit,
                    # he doesn't get any rep points.
                    if revision.userprefs.key() != prefs.key():
                        logging.info("+1 rep for editor %s" % \
                                revision.userprefs.nickname)
                        revision.userprefs.points += 1
                        revision.userprefs.put()

            # Set last activity on voting user
            prefs.date_lastactivity = datetime.datetime.now()
            prefs.put()

        self.redirect("/%s" % snippet_slug)


class SnippetEdit(webapp.RequestHandler):
    """TODO: Check if all form input is here, if user is allowed, etc"""
    def post(self, snippet_slug):
        memcache.incr("ua_edit_snippet", initial_value=0)
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)

        title = decode(self.request.get('title'))
        code = decode(self.request.get('code'))
        description = decode(self.request.get('description'))
        tags = decode(self.request.get('tags'))
        comment = decode(self.request.get('comment'))

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
        r.description_md = markdown.markdown(description).replace( \
                "<a ", "<a target='_blank' rel='nofollow' ")
        r.code = code
        r.comment = comment
        r.put()

        if prefs.key() == snippet.userprefs.key() and not snippet.has_editors:
            # Auto-merge new revision if edits only by author
            r.merge(merged_by=prefs)
        else:
            # Add proposal info if from another editor
            snippet.proposal_count += 1
            snippet.date_lastproposal = datetime.datetime.now()
            snippet.date_lastactivity = datetime.datetime.now()
            snippet.save()

        # Set last activity on submitting user
        prefs.date_lastactivity = datetime.datetime.now()
        prefs.put()

        self.redirect("/%s" % snippet_slug)


class SnippetEditView(webapp.RequestHandler):
    """Popup that shows an edit from another user"""
    def get(self, snippet_slug, rev_key):
        memcache.incr("pv_snippet_edit", initial_value=0)
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)

        rev = SnippetRevision.get(rev_key)
        #q = db.GqlQuery("SELECT * FROM SnippetRevision WHERE __key__ = :1", \
        #        db.Key(rev_key))
        #rev = q.get()  # fetch(1)[0]

        if not rev:
            self.error(404)
            return

        # TODO: memcache?
        rev.views += 1
        rev.put()

        has_voted = False
        if user:
            # see if user has already voted
            q1 = db.GqlQuery("SELECT * FROM SnippetRevisionUpvote WHERE \
                    userprefs = :1 and snippetrevision = :2", prefs, rev)
            q2 = db.GqlQuery("SELECT * FROM SnippetRevisionDownvote WHERE \
                    userprefs = :1 and snippetrevision = :2", prefs, rev)
            has_voted = q1.count() or -q2.count()  # 0 if not, 1, -1

            # Check if user wants to vote
            if not has_voted:
                has_voted = decode(self.request.get('v'))
                if has_voted == "1":
                    # user wants to upvote
                    v = SnippetRevisionUpvote(userprefs=prefs, \
                            snippetrevision=rev)
                    v.save()

                    rev.userprefs.points += 1
                    rev.userprefs.put()

                    rev.date_lastactivity = datetime.datetime.now()
                    rev.put()

                    # Set last activity on voting use0r
                    prefs.date_lastactivity = datetime.datetime.now()
                    prefs.put()

                elif has_voted == "-1":
                    # user downvotes
                    v = SnippetRevisionDownvote(userprefs=prefs, \
                            snippetrevision=rev)
                    v.save()

                    rev.userprefs.points -= 1
                    rev.userprefs.put()

                    rev.date_lastactivity = datetime.datetime.now()
                    rev.save()

                    # Set last activity on voting use0r
                    prefs.date_lastactivity = datetime.datetime.now()
                    prefs.put()

        values = {"prefs": prefs, "rev": rev, 'voted': str(has_voted), \
                'desc_md': rev.description_md}
        self.response.out.write(template.render(tdir + \
            "snippets_edit_view.html", values))


class TagView(webapp.RequestHandler):
    def get(self, tag=None):
        memcache.incr("pv_tag", initial_value=0)
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)

        if not tag:
            # Show tag list
            tags = mc.cache.tags_mostused()
            tags.sort()
            min_cnt = 0
            max_cnt = 0
            for tag, cnt in tags:
                if cnt > max_cnt:
                    max_cnt = cnt
            #logging.info("max cnt: %s" % max_cnt)
            values = {'prefs': prefs, 'tags': tags, 'max_cnt': max_cnt}
            self.response.out.write(template.render(tdir + "tags_list.html", \
                    values))
            return

        # Find base tag
        tag = tag.replace("index.html", "").strip("/")  # legacy system / goog
        #logging.info("tag: %s" % tag)
        q = Tag.all()
        q.filter("name =", tag)
        tag = q.get()

        if not tag:
            self.error(404)
            return

        # Find all snippets with tag
        #tags = SnippetTag.all()
        #tags.filter("tag =", tag)
        snippettags = tag.snippettag_set

        values = {'prefs': prefs, 'tag': tag, 'tags': \
                snippettags.order("-date_added")}
        self.response.out.write(template.render(tdir + "tags_index.html", \
                values))


class SnippetCommentView(webapp.RequestHandler):
    """Posting a comment, run through akismet to find spam"""
    def post(self, snippet_slug):
        memcache.incr("ua_comment", initial_value=0)
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)

        # Set last activity on commenting user
        prefs.date_lastactivity = datetime.datetime.now()
        prefs.put()

        q = Snippet.all()
        q.filter("slug1 =", snippet_slug)
        snippet = q.get()

        if not snippet:
            self.error(404)
            return

        comment = decode(self.request.get('comment'))
        if not comment or len(comment.strip()) == 0:
            self.redirect("/%s" % snippet_slug)
            return

        # Add the comment now
        c = SnippetComment(userprefs=prefs, snippet=snippet, comment=comment)
        c.comment_md = markdown.markdown(comment).replace( \
                "<a ", "<a target='_blank' rel='nofollow' ")

        # Check if comment is spam
        try:
            real_key = akismet.verify_key(settings.AKISMET_APIKEY, \
                settings.AKISMET_URL)
            if real_key:
                is_spam = akismet.comment_check(settings.AKISMET_APIKEY, \
                    settings.AKISMET_URL, \
                    self.request.remote_addr, \
                    self.request.headers["User-Agent"], \
                    comment_content=comment)
                if is_spam:
                    memcache.incr("ua_comment_spam", initial_value=1)
                    logging.warning("= comment: Yup, that's spam alright.")
                    c.flagged_as_spam = True
                    url_addon = "?c=m"
                else:
                    memcache.incr("ua_comment_ham", initial_value=1)
                    logging.info("= comment: Hooray, your users aren't scum!")
                    url_addon = ""
                    snippet.comment_count += 1
                    snippet.date_lastcomment = datetime.datetime.now()
                    snippet.save()
        except akismet.AkismetError, e:
            logging.error("%s, %s" % (e.response, e.statuscode))

        c.save()

        self.redirect("/%s%s#comments" % (snippet_slug, url_addon))


class AboutView(webapp.RequestHandler):
    def get(self, category=None):
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)
        values = {'prefs': prefs}

        if not category:
            self.response.out.write( \
                    template.render(tdir + "about.html", values))

    def post(self, category=None):
        """Feedback form post"""
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)
        values = {'prefs': prefs}

        msg = decode(self.request.get('msg'))
        #logging.info("msg: %s" % msg)
        if msg:
            if prefs:
                sender = "%s (%s)" % (prefs.nickname, prefs.email)
            else:
                sender = decode(self.request.get('email'))
            logging.info("feedback '%s' from %s" % (msg, sender))
            message = mail.EmailMessage()
            message.sender = "Android Snippets <chris@androidsnippets.com>"
            message.to = "chris@metachris.org"
            message.subject = "Android snippets feedback form"
            message.body = "Feedback from: %s:\n\n%s" % (sender, msg)
            message.send()

            values["info"] = "Thank you, we have received your feedback."

        self.response.out.write( \
                template.render(tdir + "about.html", values))


class SearchView(webapp.RequestHandler):
    def get(self):
        memcache.incr("pv_search", initial_value=0)
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)
        q = decode(self.request.get('q'))

        values = {'prefs': prefs, 'q': q}
        self.response.out.write( \
                template.render(tdir + "search_results.html", values))


class UsersView(webapp.RequestHandler):
    def get(self):
        memcache.incr("pv_userlist", initial_value=0)
        user = users.get_current_user()
        prefs = InternalUser.from_user(user)

        q = decode(self.request.get('q'))
        p = decode(self.request.get('p'))

        _users = InternalUser.all()
        if q == "1" or not q:
            _users.order("-points")
        else:
            #_users.filter("date_lastactivity !=", None)
            _users.order("-date_lastactivity")

        page = int(p) if p else 1
        items_per_page = 40
        n = items_per_page / 2
        offset = (page - 1) * items_per_page
        _users1 = _users.fetch(n, offset)
        _users2 = _users.fetch(n, (offset + (items_per_page / 2)))

        values = {'prefs': prefs, 'users1': _users1, 'users2': _users2,
                'page': page, 'pages': range(1, page), 'prefix': q}
        self.response.out.write( \
                template.render(tdir + "users.html", values))
