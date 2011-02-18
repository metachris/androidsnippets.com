from google.appengine.ext import db
from google.appengine.api import users

import logging
import datetime
from hashlib import md5


class UserPrefs(db.Model):
    """Extended user preferences"""
    user = db.UserProperty(required=True)
    nickname = db.StringProperty(required=False)
    email = db.StringProperty(required=True)
    email_md5 = db.StringProperty()  # used for gravatar

    date_joined = db.DateTimeProperty(auto_now_add=True)
    date_lastlogin = db.DateTimeProperty(auto_now=True)

    # user access levels. 0=default, 1=editor, 2=admin
    level = db.IntegerProperty(default=0)

    karma = db.IntegerProperty(default=1)
    points = db.IntegerProperty(default=1)

    # How to submit guidelines
    has_accepted_terms0 = db.BooleanProperty(default=False)

    @staticmethod
    def from_user(user):
        if not user:
            return None

        # Valid user, now lets see if we have a userpref object in the db
        q = db.GqlQuery("SELECT * FROM UserPrefs WHERE user = :1", user)
        prefs = q.get()
        if not prefs:
            # First time for this user, create userpref object now
            m = md5(user.email().strip().lower()).hexdigest()
            prefs = UserPrefs(user=user, nickname=user.nickname(), \
                        email=user.email(), email_md5=m)
            prefs.put()
        return prefs


class Achievement(db.Model):
    """Achievement of a user"""
    user = db.UserProperty(required=True)
    achievement_id = db.IntegerProperty(default=0)
    achievement_title = db.StringProperty()
    date_earned = db.DateTimeProperty(auto_now_add=True)


class Snippet(db.Model):
    """
    One snippet gets the votes, but all it's content stored in SnippetRevisions
    starting with revision_id=0. All votes point to this snippet, whereas one
    snippet can have multiple revisions of content (community wiki).

    This is always the current "master" revision. Others can be merged into
    that one.

    Submitter is the user with the oldest Revision.
    """
    date_submitted = db.DateTimeProperty(auto_now_add=True)

    # infos for building the urls to this snippet
    slug1 = db.StringProperty()  # new snippets get referenced by slug and id
    slug2 = db.StringProperty()  # old snippets set slug2 to old id

    # Number of pageviews
    views = db.IntegerProperty(default=1)

    # LastActivity includes edits, comments and votes
    date_lastactivity = db.DateTimeProperty(auto_now_add=True)

    # update_count: how many times this snippet was updated
    update_count = db.IntegerProperty(default=0)
    date_lastupdate = db.DateTimeProperty(auto_now_add=True)

    def was_updated(self):
        self.update_count += 1
        self.date_lastupdate = datetime.datetime.now()
        self.date_lastactivity = datetime.datetime.now()

    # proposal_count: how many proposals are currently unreviewed
    proposal_count = db.IntegerProperty(default=0)
    date_lastproposal = db.DateTimeProperty(auto_now_add=True)

    def was_edited(self):
        self.proposal_count += 1
        self.date_lastproposal = datetime.datetime.now()
        self.date_lastactivity = datetime.datetime.now()

    # Vote information
    upvote_count = db.IntegerProperty(default=1)
    date_lastvote = db.DateTimeProperty(auto_now_add=True)  # up or downvote
    date_lastupvote = db.DateTimeProperty(auto_now_add=True)

    def upvote(self):
        self.upvote_count += 1
        self.date_lastvote = datetime.datetime.now()
        self.date_lastupvote = datetime.datetime.now()
        self.date_lastactivity = datetime.datetime.now()

    # Rating - To be defined (for now count of upvotes).
    rating = db.IntegerProperty(default=1)

    # content attributes, copied over from the revision
    title = db.StringProperty()
    description = db.TextProperty()
    code = db.TextProperty()
    android_minsdk = db.IntegerProperty(default=0)
    categories = db.StringListProperty(default=[])
    tags = db.StringListProperty(default=[])


class SnippetUpvote(db.Model):
    """Vote on a snippet"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    date = db.DateTimeProperty(auto_now_add=True)


class SnippetRevision(db.Model):
    """A revision is a new version with edits by another user (suggestions
    how this snippet could be better). held in  moderation until approved."""
    snippet = db.ReferenceProperty(Snippet, required=True)
    editor = db.UserProperty(required=True)

    # author's comment about this changeset
    revision_description = db.TextProperty()
    date_submitted = db.DateTimeProperty(auto_now_add=True)

    approved = db.BooleanProperty(default=False)
    approved_by = db.UserProperty()
    approved_date = db.DateTimeProperty()

    rejected = db.BooleanProperty(default=False)
    rejected_by = db.UserProperty()
    rejected_date = db.DateTimeProperty()

    # content attributes - copied over into Snippet class on merge
    title = db.StringProperty()
    description = db.TextProperty()
    code = db.TextProperty()
    android_minsdk = db.IntegerProperty(default=0)
    categories = db.StringListProperty(default=[])
    tags = db.StringListProperty(default=[])

    @staticmethod
    def create_first_revision(user, snippet):
        """When a snippet is created, this creates the first revision"""
        r = SnippetRevision(editor=user, snippet=snippet)
        r.revision_description = "initial commit"
        r.date_submitted = datetime.datetime.now()
        r.approved = True
        r.approved_by = user
        r.approved_date = datetime.datetime.now()
        r.title = snippet.title
        r.description = snippet.description
        r.code = snippet.code
        r.android_minsdk = snippet.android_minsdk
        r.categories = snippet.categories
        r.tags = snippet.tags
        return r


class SnippetRevisionUpvote(db.Model):
    """Vote on a snippet revision held in moderation"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(SnippetRevision, required=True)


class SnippetComment(db.Model):
    """Comment on a snippet"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    parent_comment = db.SelfReferenceProperty()

    date_submitted = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now=True)
    edits_count = db.IntegerProperty(default=0)

    comment = db.TextProperty(required=False)


class SnippetRevisionComment(db.Model):
    """Comment on a snippet revision which may be held in moderation"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(SnippetRevision, required=True)
    parent_comment = db.SelfReferenceProperty()

    date_submitted = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now_add=True)
    edits_count = db.IntegerProperty(default=0)

    comment = db.TextProperty()


class Tag(db.Model):
    """
    For each tag there is one tag object in order to be able to get a list
    of unique tags, and to get usage count with ``Tag.snippettag_set.count()``
    """
    name = db.StringProperty(required=True)
    date_added = db.DateTimeProperty(auto_now_add=True)


class SnippetTag(db.Model):
    """Associates a tag with a snippet"""
    snippet = db.ReferenceProperty(Snippet, required=True)
    tag = db.ReferenceProperty(Tag, required=True)

    date_added = db.DateTimeProperty(auto_now_add=True)
