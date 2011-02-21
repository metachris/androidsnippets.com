from google.appengine.ext import db
from google.appengine.api import users

import logging
import datetime
from hashlib import md5

"""
Relations to user object
------------------------
To be able to access user preferences (eg. email_md5 for gravatar) all models
reference UserPrefs instead of directly the user property.
"""


class UserPrefs(db.Model):
    """Extended user preferences"""
    user = db.UserProperty(required=True)
    nickname = db.StringProperty(required=False)
    email = db.StringProperty(required=True)
    email_md5 = db.StringProperty(required=True)  # used for gravatar

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
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    achievement_id = db.IntegerProperty(default=0)
    achievement_title = db.StringProperty()
    date_earned = db.DateTimeProperty(auto_now_add=True)


class Snippet(db.Model):
    """
    The snippet model always contains the latest version, and all votes and
    comments are linked to this model.

    One snippet model can have multiple SnippetRevisions, which are edits
    by the author or other users. By default Revisions are only suggestions.
    If a revision gets enough upvotes it will be automatically merged, if it
    gets enough downvotes it will be deleted.
    """
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    date_submitted = db.DateTimeProperty(auto_now_add=True)

    # infos for building the urls to this snippet
    slug1 = db.StringProperty()  # new snippets get referenced by slug1
    slug2 = db.StringProperty()  # old snippets haveset slug2 to old id

    # Number of pageviews
    views = db.IntegerProperty(default=0)

    # LastActivity includes edits, comments and votes
    date_lastactivity = db.DateTimeProperty(auto_now_add=True)

    # update_count: how many merges from new revisions
    update_count = db.IntegerProperty(default=0)
    date_lastupdate = db.DateTimeProperty(auto_now_add=True)

    # proposal_count: how many proposals are currently in review queue
    proposal_count = db.IntegerProperty(default=0)
    date_lastproposal = db.DateTimeProperty(auto_now_add=True)

    # Vote information
    upvote_count = db.IntegerProperty(default=1)
    downvote_count = db.IntegerProperty(default=1)
    date_lastvote = db.DateTimeProperty(auto_now_add=True)  # up or downvote
    date_lastdownvote = db.DateTimeProperty(auto_now_add=True)

    # Rating - To be defined (for now sum of up- and downvotes)
    rating = db.IntegerProperty(default=1)

    def upvote(self):
        """Adjust snippet properties after upvote"""
        self.rating += 10
        self.upvote_count += 1
        self.date_lastvote = datetime.datetime.now()
        self.date_lastupvote = datetime.datetime.now()
        self.date_lastactivity = datetime.datetime.now()

    def downvote(self):
        """Adjust snippet properties after downvote"""
        self.rating -= 10
        self.downvote_count += 1
        self.date_lastvote = datetime.datetime.now()
        self.date_lastdownvote = datetime.datetime.now()
        self.date_lastactivity = datetime.datetime.now()

    # content attributes, copied over from the revision
    title = db.StringProperty()
    description = db.TextProperty()
    code = db.TextProperty()
    android_minsdk = db.IntegerProperty(default=0)
    categories = db.StringListProperty(default=[])
    tags = db.StringListProperty(default=[])


class SnippetUpvote(db.Model):
    """Upvote on a snippet"""
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    date = db.DateTimeProperty(auto_now_add=True)


class SnippetDownvote(db.Model):
    """Upvote on a snippet"""
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    date = db.DateTimeProperty(auto_now_add=True)


class SnippetFollow(db.Model):
    """Follower on a snippet"""
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    date = db.DateTimeProperty(auto_now_add=True)


class SnippetRevision(db.Model):
    """
    A revision is a new version with edits by another user (suggestions
    how this snippet could be better). held in  moderation until approved
    or rejected (by upvotes and downvotes).
    """
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    date_submitted = db.DateTimeProperty(auto_now_add=True)

    # Number of pageviews
    views = db.IntegerProperty(default=0)

    # author's comment about this changeset
    revision_description = db.TextProperty()

    # has been merged?
    merged = db.BooleanProperty(default=False)
    merged_by = db.ReferenceProperty(UserPrefs, \
            collection_name="mergedrevision_set")
    merged_date = db.DateTimeProperty()

    # has been rejected?
    rejected = db.BooleanProperty(default=False)
    rejected_by = db.ReferenceProperty(UserPrefs, \
            collection_name="rejectedrevision_set")
    rejected_date = db.DateTimeProperty()

    # content attributes - copied over into Snippet class on merge
    title = db.StringProperty()
    description = db.TextProperty()
    code = db.TextProperty()
    android_minsdk = db.IntegerProperty(default=0)
    categories = db.StringListProperty(default=[])
    tags = db.StringListProperty(default=[])

    def merge(self, merged_by):
        """Merges this revision into the snippet (updates snippet and
        saves snippet to database)."""
        self.snippet.title = self.title
        self.snippet.description = self.description
        self.snippet.code = self.code
        self.snippet.android_minsdk = self.android_minsdk
        self.snippet.categories = self.categories
        self.snippet.tags = self.tags

        self.snippet.update_count += 1
        self.snippet.date_lastupdate = datetime.datetime.now()
        self.snippet.date_lastactivity = datetime.datetime.now()

        self.snippet.put()

        self.merged = True
        self.merged_by = merged_by
        self.merged_date = datetime.datetime.now()
        self.put()

    @staticmethod
    def create_first_revision(userprefs, snippet):
        """When a snippet is created, this creates the first revision"""
        r = SnippetRevision(userprefs=userprefs, snippet=snippet)
        r.revision_description = "initial commit"
        r.date_submitted = datetime.datetime.now()
        r.title = snippet.title
        r.description = snippet.description
        r.code = snippet.code
        r.android_minsdk = snippet.android_minsdk
        r.categories = snippet.categories
        r.tags = snippet.tags

        # Auto-approve the initial revision.
        # snippet was already updated at creation
        r.merged = True
        r.merged_by = userprefs
        r.merged_date = datetime.datetime.now()

        return r


class SnippetRevisionUpvote(db.Model):
    """Vote on a snippet revision held in moderation"""
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    snippetrevision = db.ReferenceProperty(SnippetRevision, required=True)


class SnippetRevisionDownvote(db.Model):
    """Downvote on a snippet revision held in moderation"""
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    snippetrevision = db.ReferenceProperty(SnippetRevision, required=True)


class SnippetComment(db.Model):
    """Comment on a snippet"""
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    parent_comment = db.SelfReferenceProperty()

    date_submitted = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now=True)
    edits_count = db.IntegerProperty(default=0)

    comment = db.TextProperty(required=False)
    comment_md = db.TextProperty(required=False)


class SnippetRevisionComment(db.Model):
    """Comment on a snippet revision which may be held in moderation"""
    userprefs = db.ReferenceProperty(UserPrefs, required=True)
    snippetrevision = db.ReferenceProperty(SnippetRevision, required=True)
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
