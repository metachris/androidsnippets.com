import os
import logging
import datetime

from google.appengine.api import users
from google.appengine.api import memcache

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp import template

import markdown
import akismet

from time import sleep
from tools import slugify, decode, get_tags_mostused
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


# Custom sites
class Main(webapp.RequestHandler):
    def get(self):
        memcache.incr("pv_main", initial_value=0)
        user = users.get_current_user()

        """
        if user:
            logging.info("== user email: %s" % user.email())
            logging.info("== user nickname: %s" % user.nickname())
            logging.info("== user id: %s" % user.user_id())
            logging.info("== fed id: %s" % user.federated_identity())
            logging.info("== fed provider: %s" % user.federated_provider())
        """
        prefs = UserPrefs.from_user(user)

        #logging.info("== %s" % self.request.cookies)
        #logging.info("== %s" % self.request.headers)
        #logging.info("== %s" % self.request.remote_addr)

        q = Snippet.all()
        q.order("-date_submitted")
        snippets = q.fetch(20)

        values = {'prefs': prefs, 'snippets': snippets}
        self.response.out.write(template.render(tdir + "index.html", values))


class LegacySnippetView(webapp.RequestHandler):
    """Redirects for snippets of legacy androidsnippets.org, which have
    links such as http://androidsnippets.org/snippets/198

    Also handles /snippets/new, /snippets/active, etc.
    """
    def get(self, legacy_slug):
        if legacy_slug in ["new", "active", "edits", "popular", "comments"]:
            user = users.get_current_user()
            prefs = UserPrefs.from_user(user)
            q = Snippet.all()
            if legacy_slug == "new":
                q.order("-date_submitted")
                title = "New Snippets"
            elif legacy_slug == "active":
                q.order("-date_lastactivity")
                title = "Active Snippets"
            elif legacy_slug == "popular":
                q.order("-upvote_count")
                title = "Popular Snippets"
            elif legacy_slug == "comments":
                q.order("-comment_count")
                title = "Recently Commented Snippets"
            elif legacy_slug == "edits":
                q.filter("proposal_count >", 0)
                q.order("proposal_count")
                title = "Snippets with Edits"
            snippets = q.fetch(20)
            values = {'prefs': prefs, 'snippets': snippets, 'title': title}
            self.response.out.write(template.render(tdir + \
                    "snippet_list.html", values))
            return

        memcache.incr("pv_snippet_legacy", initial_value=0)
        legacy_slug = legacy_slug.strip("index.html").strip("/")
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
        memcache.incr("pv_snippet", initial_value=0)
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        q = Snippet.all()
        q.filter("slug1 =", snippet_slug)
        snippet = q.get()

        if not snippet:
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
                {"comments": comments})

        # markdown the description
        # desc_md = markdown.markdown(snippet.description)

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
        prefs = UserPrefs.from_user(user)

        if not user:
            self.response.out.write("-1")
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

        if vote:
            # Has already voted
            # self.response.out.write("0")
            pass
        else:
            # Create the upvote
            u = SnippetUpvote(userprefs=prefs, snippet=snippet)
            u.save()
            snippet.upvote()
            snippet.save()
            # self.response.out.write("1")

        self.redirect("/%s" % snippet_slug)


class SnippetEdit(webapp.RequestHandler):
    """TODO: Check if all form input is here, if user is allowed, etc"""
    def post(self, snippet_slug):
        memcache.incr("ua_edit_snippet", initial_value=0)
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

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
                "<a ", "<a target='_blank' ")
        r.code = code
        r.comment = comment
        r.put()

        if user == snippet.userprefs.user:
            # Auto-merge new revision if edit by author
            r.merge(merged_by=prefs)
            # self.response.out.write("0")
        else:
            # Add proposal info if from another editor
            snippet.proposal_count += 1
            snippet.date_lastproposal = datetime.datetime.now()
            snippet.date_lastactivity = datetime.datetime.now()
            snippet.save()
            # self.response.out.write("1")

        self.redirect("/%s" % snippet_slug)


class SnippetEditView(webapp.RequestHandler):
    """Popup that shows an edit from another user"""
    def get(self, snippet_slug, rev_key):
        memcache.incr("pv_snippet_edit", initial_value=0)
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

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

            if not has_voted:
                # Check if user wantsto vote
                has_voted = decode(self.request.get('v'))
                if has_voted == "1":
                    # user wants to upvote
                    v = SnippetRevisionUpvote(userprefs=prefs, \
                            snippetrevision=rev)
                    v.save()
                elif has_voted == "-1":
                    # user downvotes
                    v = SnippetRevisionDownvote(userprefs=prefs, \
                            snippetrevision=rev)
                    v.save()

        # TODO: memcache
        desc_md = markdown.markdown(rev.description)
        values = {"prefs": prefs, "rev": rev, 'voted': str(has_voted), \
                'desc_md': desc_md}
        self.response.out.write(template.render(tdir + \
            "snippets_edit_view.html", values))


class TagView(webapp.RequestHandler):
    def get(self, tag=None):
        memcache.incr("pv_tag", initial_value=0)
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

        if not tag:
            # Show tag list
            tags = get_tags_mostused()
            tags.sort()
            min_cnt = 0
            max_cnt = 0
            for tag, cnt in tags:
                if cnt > max_cnt:
                    max_cnt = cnt
            logging.info("max cnt: %s" % max_cnt)
            values = {'prefs': prefs, 'tags': tags, 'max_cnt': max_cnt}
            self.response.out.write(template.render(tdir + "tags_list.html", \
                    values))
            return

        # Find base tag
        tag = tag.strip("index.html").strip("/")  # legacy system / google
        q = Tag.all()
        q.filter("name =", tag)
        tag = q.get()

        if not tag:
            self.error(404)
            return

        # Find all snippets with tag
        tags = SnippetTag.all()
        tags.filter("tag =", tag)

        values = {'prefs': prefs, 'tag': tag, 'tags': tags}
        self.response.out.write(template.render(tdir + "tags_index.html", \
                values))


class SnippetCommentView(webapp.RequestHandler):
    """Posting a comment, run through akismet to find spam"""
    def post(self, snippet_slug):
        memcache.incr("ua_comment", initial_value=0)
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)

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
        comment_md = markdown.markdown(comment)
        c = SnippetComment(userprefs=prefs, snippet=snippet, comment=comment)
        c.comment_md = comment_md

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
        prefs = UserPrefs.from_user(user)
        values = {'prefs': prefs}

        if not category:
            self.response.out.write( \
                    template.render(tdir + "about.html", values))

        if category == "/stats":
            for item in mc_items:
                values["stats"].append((item, memcache.get(item)))
            self.response.out.write( \
                    template.render(tdir + "admin_stats.html", values))

        if category == "/stats/reset":
            for item in mc_items:
                memcache.set(item, 0)
            self.redirect("/admin/stats")


class SearchView(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        prefs = UserPrefs.from_user(user)
        q = decode(self.request.get('q'))

        values = {'prefs': prefs, 'q': q}
        self.response.out.write( \
                template.render(tdir + "search_results.html", values))
