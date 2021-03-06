from google.appengine.ext import db

from google.appengine.api import users
from google.appengine.api import memcache

import logging
import datetime
from hashlib import md5

"""
Relations to user object
------------------------
To be able to access user preferences (eg. email_md5 for gravatar) all models
reference UserPrefs instead of directly the user property.
"""


class InternalUser(db.Model):
    """Extended user preferences

    If email is provided by openid, is is marked as verified,
    else a user has to verify the email address.
    """
    nickname = db.StringProperty()
    email = db.StringProperty(default="")
    email_md5 = db.StringProperty(default="")  # used for gravatar

    federated_identity = db.StringProperty()
    federated_provider = db.StringProperty()

    # Unverified email and verification code
    email_new = db.StringProperty()
    email_new_code = db.StringProperty()

    date_joined = db.DateTimeProperty(auto_now_add=True)
    date_lastlogin = db.DateTimeProperty(auto_now_add=True)  # TODO
    date_lastactivity = db.DateTimeProperty(auto_now_add=True)

    twitter = db.StringProperty(default="")  # twitter username
    about = db.TextProperty(default="")
    about_md = db.TextProperty(default="")

    # notifications are a bitfield. default: lower 8 bits set to 1 (all on)
    notifications = db.IntegerProperty(default=255)

    # user level. 0=default, 1=editor, 100=admin
    level = db.IntegerProperty(default=0)

    # reputation
    points = db.IntegerProperty(default=1)
    points_edits = db.IntegerProperty(default=0)

    # unused
    karma = db.IntegerProperty(default=1)

    # How to submit guidelines
    has_accepted_terms0 = db.BooleanProperty(default=False)

    # Has this user unread messages in his inbox
    messages_unread = db.IntegerProperty(default=0)

    # google user id is only used on the dev server
    google_user_id = db.StringProperty()

    # legacy system infos
    legacy_user_id = db.IntegerProperty(default=0)  # to re-associate snippets
    legacy_email = db.StringProperty()
    legacy_federated_identity = db.StringProperty()

    def clear_cache(self):
        logging.info("clear cached prefs")
        if self.federated_identity and self.federated_provider:
            key = "prefs_f_%s%s" % (self.federated_identity, \
                    self.federated_provider)
        elif self.google_user_id:
            key = "prefs_g_%s" % self.google_user_id
        memcache.delete(key)

    @staticmethod
    def mcfrom_user(user):
        """Return InternalUser object -- from memcache if possible"""
        if not user:
            return None

        if user.federated_identity() and user.federated_provider():
            key = "prefs_f_%s%s" % (user.federated_identity(), \
                    user.federated_provider())
        elif user.user_id():
            key = "prefs_g_%s" % user.user_id()

        #logging.info("k: %s" % key)

        prefs = memcache.get(key)
        if prefs:
            #logging.info("return cached prefs k: %s" % key)
            return prefs

        #logging.info("rebuild k: %s" % key)
        # cache prefs now
        userprefs = InternalUser._from_user(user)
        memcache.set(key, userprefs)
        return userprefs

    @staticmethod
    def from_user(user):
        if not user:
            return None

        if not user.federated_identity():
            logging.warning("_ user has no fed id [%s]" % user)
            #return

        if user.federated_identity():
            q = db.GqlQuery("SELECT * FROM InternalUser WHERE \
                federated_identity = :1 AND federated_provider = :2", \
                user.federated_identity(), user.federated_provider())
        else:
            q = db.GqlQuery("SELECT * FROM InternalUser WHERE \
                google_user_id = :1", user.user_id())
        prefs = q.get()

        # most of the time we will return an already saved prefs
        # if not, check if user has legacy prefs stored
        if not prefs:
            if user.email():
                logging.info("_ looking for legacy prefs by email [%s]" % \
                    user.email())
                q = db.GqlQuery("SELECT * FROM InternalUser WHERE \
                    legacy_email = :1", user.email())
                prefs = q.get()

            # if not legacy prefs by email, check if user has legacy prefs
            if not prefs and user.federated_identity():
                logging.info("_ looking for legacy prefs by fedid [%s]" % \
                    user.federated_identity())
                q = db.GqlQuery("SELECT * FROM InternalUser WHERE \
                    legacy_federated_identity = :1", user.federated_identity())
                prefs = q.get()

            # if legacy prefs found, add new information
            if prefs:
                logging.info("_ legacy prefs found. updating")
                if user.email():
                    prefs.email = user.email()
                elif prefs.legacy_email:
                    prefs.email = prefs.legacy_email
                prefs.legacy_email = None
                if user.federated_identity():
                    prefs.federated_identity = user.federated_identity()
                    prefs.federated_provider = user.federated_provider()
                    prefs.legacy_federated_identity = None
                prefs.put()

        if not prefs:
            # create regular new userpref object now
            nick = user.nickname()
            if user.email():
                if not nick or "http://" in nick:
                    nick = user.email()

            m = md5(user.email().strip().lower()).hexdigest()

            logging.info("_ create new openid prefs")
            fed_id = user.federated_identity()
            fed_prov = user.federated_provider()
            prefs = InternalUser(federated_identity=fed_id,\
                federated_provider=fed_prov, nickname=nick, \
                email=user.email(), email_md5=m)
            prefs.google_user_id = user.user_id()
            prefs.put()

        return prefs

    @staticmethod
    def from_data(nickname, email, datetime_joined, fed_id=None, \
            legacy_id=None):
        """Creates an orphaned prefs object (one without user).
        Used for imports from the legacy database. Once a user
        with matching email registers, it will be assigned."""
        if not email or not nickname or not datetime_joined:
            return

        # Valid data
        m = md5(email.strip().lower()).hexdigest()
        prefs = InternalUser(nickname=nickname, email=email, \
            legacy_email=email, email_md5=m)
        prefs.date_joined = datetime_joined
        if fed_id:
            prefs.legacy_federated_identity = fed_id
        if legacy_id:
            prefs.legacy_user_id = legacy_id
        prefs.put()
        return prefs


class Achievement(db.Model):
    """Achievement of a user"""
    userprefs = db.ReferenceProperty(InternalUser, required=True)
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
    userprefs = db.ReferenceProperty(InternalUser, required=True)
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

    # if this snippet has been edited by other users than author,
    # the author cannot override them anymore without review
    has_editors = db.BooleanProperty(default=False)

    # proposal_count: how many proposals are currently in review queue
    proposal_count = db.IntegerProperty(default=0)
    date_lastproposal = db.DateTimeProperty()

    # comment_count
    comment_count = db.IntegerProperty(default=0)
    date_lastcomment = db.DateTimeProperty()

    # Vote information
    upvote_count = db.IntegerProperty(default=1)
    downvote_count = db.IntegerProperty(default=0)
    date_lastvote = db.DateTimeProperty(auto_now_add=True)  # up or downvote
    date_lastdownvote = db.DateTimeProperty()

    # Rating - To be defined (for now sum of up- and downvotes)
    rating = db.IntegerProperty(default=1)

    def upvote(self):
        """Adjust snippet properties after upvote"""
        self.rating += 10  # unused
        self.upvote_count += 1
        self.date_lastvote = datetime.datetime.now()
        self.date_lastupvote = datetime.datetime.now()
        self.date_lastactivity = datetime.datetime.now()

    def downvote(self):  # unused
        """Adjust snippet properties after downvote"""
        self.rating -= 10
        self.downvote_count += 1
        self.date_lastvote = datetime.datetime.now()
        self.date_lastdownvote = datetime.datetime.now()
        self.date_lastactivity = datetime.datetime.now()

    # content attributes, copied over from the revision
    title = db.StringProperty()
    description = db.TextProperty()
    description_md = db.TextProperty()
    code = db.TextProperty()
    android_minsdk = db.IntegerProperty(default=0)
    categories = db.StringListProperty(default=[])
    tags = db.StringListProperty(default=[])


class SnippetUpvote(db.Model):
    """Upvote on a snippet"""
    userprefs = db.ReferenceProperty(InternalUser, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    date = db.DateTimeProperty(auto_now_add=True)


class SnippetDownvote(db.Model):
    """Upvote on a snippet"""
    userprefs = db.ReferenceProperty(InternalUser, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    date = db.DateTimeProperty(auto_now_add=True)


class SnippetFollow(db.Model):
    """Follower on a snippet"""
    userprefs = db.ReferenceProperty(InternalUser, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    date = db.DateTimeProperty(auto_now_add=True)


class SnippetRevision(db.Model):
    """
    A revision is a new version with edits by another user (suggestions
    how this snippet could be better). held in  moderation until approved
    or rejected (by upvotes and downvotes).
    """
    userprefs = db.ReferenceProperty(InternalUser, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    date_submitted = db.DateTimeProperty(auto_now_add=True)
    comment = db.TextProperty()  # author's comment
    initial_revision = db.BooleanProperty(default=False)

    # unused
    views = db.IntegerProperty(default=0)

    # last up or downvote on this revision
    date_lastactivity = db.DateTimeProperty(auto_now=True)

    # has been merged?
    merged = db.BooleanProperty(default=False)
    merged_by = db.ReferenceProperty(InternalUser, \
            collection_name="mergedrevision_set")
    merged_date = db.DateTimeProperty()

    # has been rejected?
    rejected = db.BooleanProperty(default=False)
    rejected_by = db.ReferenceProperty(InternalUser, \
            collection_name="rejectedrevision_set")
    rejected_date = db.DateTimeProperty()

    # content attributes - copied over into Snippet class on merge
    title = db.StringProperty()
    description = db.TextProperty()
    description_md = db.TextProperty()
    code = db.TextProperty()
    android_minsdk = db.IntegerProperty(default=0)
    categories = db.StringListProperty(default=[])
    tags = db.StringListProperty(default=[])

    def merge(self, merged_by):
        """Merges this revision into the snippet (updates snippet and
        saves snippet to database)."""
        self.snippet.title = self.title
        self.snippet.description = self.description
        self.snippet.description_md = self.description_md
        self.snippet.code = self.code
        self.snippet.android_minsdk = self.android_minsdk
        self.snippet.categories = self.categories
        self.snippet.tags = self.tags

        # if edit from author, proposal count was never increased, else decr
        if self.userprefs.key() != self.snippet.userprefs.key():
            self.snippet.proposal_count -= 1
        self.snippet.update_count += 1
        self.snippet.date_lastupdate = datetime.datetime.now()
        self.snippet.date_lastactivity = datetime.datetime.now()

        self.snippet.put()

        self.merged = True
        self.merged_by = merged_by
        self.merged_date = datetime.datetime.now()
        self.put()

        # Submitter of edit gets reputation points, if not original author
        if self.userprefs.key() != self.snippet.userprefs.key():
            self.userprefs.points += 2
            self.userprefs.put()

    @staticmethod
    def create_first_revision(userprefs, snippet):
        """When a snippet is created, this creates the first revision"""
        r = SnippetRevision(userprefs=userprefs, snippet=snippet)
        r.comment = "initial commit"
        r.date_submitted = datetime.datetime.now()
        r.title = snippet.title
        r.description = snippet.description
        r.code = snippet.code
        r.android_minsdk = snippet.android_minsdk
        r.categories = snippet.categories
        r.tags = snippet.tags
        r.initial_revision = True

        # Auto-approve the initial revision.
        # snippet was already updated at creation
        r.merged = True
        r.merged_by = userprefs
        r.merged_date = datetime.datetime.now()

        return r


class SnippetRevisionUpvote(db.Model):
    """Vote on a snippet revision held in moderation"""
    userprefs = db.ReferenceProperty(InternalUser, required=True)
    snippetrevision = db.ReferenceProperty(SnippetRevision, required=True)


class SnippetRevisionDownvote(db.Model):
    """Downvote on a snippet revision held in moderation"""
    userprefs = db.ReferenceProperty(InternalUser, required=True)
    snippetrevision = db.ReferenceProperty(SnippetRevision, required=True)


class SnippetComment(db.Model):
    """Comment on a snippet"""
    userprefs = db.ReferenceProperty(InternalUser, required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)
    parent_comment = db.SelfReferenceProperty()

    date_submitted = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now=True)
    edits_count = db.IntegerProperty(default=0)

    comment = db.TextProperty(required=False)
    comment_md = db.TextProperty(required=False)

    flagged_as_spam = db.BooleanProperty(default=False)


class SnippetRevisionComment(db.Model):
    """Comment on a snippet revision which may be held in moderation"""
    userprefs = db.ReferenceProperty(InternalUser, required=True)
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


class Message(db.Model):
    """Message from a user to a user or a group"""
    sender = db.ReferenceProperty(InternalUser, \
        collection_name="messagesent_set")
    recipient = db.ReferenceProperty(InternalUser)
    recipient_group = db.IntegerProperty()

    subject = db.StringProperty()
    message = db.TextProperty()

    read = db.BooleanProperty(default=False)
    date = db.DateTimeProperty(auto_now_add=True)
