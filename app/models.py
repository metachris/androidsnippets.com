from google.appengine.ext import db
from google.appengine.api import users

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
    """
    # non-changing attributes
    submitter = db.UserProperty(required=True)
    date_submitted = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now=True)

    # infos for building the urls to this snippet
    slug1 = db.StringProperty()  # new snippets get referenced by slug and id
    slug2 = db.StringProperty()  # old snippets set slug2 to old id

    # default revision reference. of many content revisions any can be default.
    revision_set = db.IntegerProperty(default=1)
    revision_count = db.IntegerProperty(default=1)

    views = db.IntegerProperty(default=0)

    def get_current_revision(self):
        return db.GqlQuery("SELECT * FROM SnippetRevision WHERE \
            revision_id = :1", self.revision_set).get()

    # content attributes, copied over from revision for easy access
    title = db.StringProperty()
    description = db.TextProperty()
    code = db.TextProperty()
    compatible_android_versions = db.ListProperty(int, default=[])

    categories = db.StringListProperty(default=[])
    tags = db.StringListProperty(default=[])


class SnippetRevision(db.Model):
    """Content revision of a snippet. If new suggestion by another dev, it is
    held in  moderation until approved."""
    snippet = db.ReferenceProperty(Snippet, required=True)
    contributor = db.UserProperty(required=True)
    revision_id = db.IntegerProperty(default=1)  # 1 is always initial revision
    revision_title = db.StringProperty()  # title for changeset by author

    approved = db.BooleanProperty(default=False)
    approved_by = db.UserProperty()

    date_submitted = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now=True)
    edits_count = db.IntegerProperty(default=0)

    # content attributes
    title = db.StringProperty()
    description = db.TextProperty()
    code = db.TextProperty()
    compatible_android_versions = db.ListProperty(int, default=[])

    categories = db.StringListProperty(default=[])
    tags = db.StringListProperty(default=[])


class SnippetUpvote(db.Model):
    """Vote on a snippet"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)


class SnippetRevisionUpvote(db.Model):
    """Vote on a snippet revision held in moderation"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(SnippetRevision, required=True)


class SnippetComment(db.Model):
    """Comment on a snippet"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)

    date_submitted = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now=True)
    edits_count = db.IntegerProperty(default=0)

    comment = db.TextProperty(required=False)


class SnippetRevisionComment(db.Model):
    """Comment on a snippet revision which may be held in moderation"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(SnippetRevision, required=True)

    date_submitted = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now_add=True)
    edits_count = db.IntegerProperty(default=0)

    comment = db.TextProperty()
