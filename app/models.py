from google.appengine.ext import db
from google.appengine.api import users


class UserPrefs(db.Model):
    """Extended user preferences"""
    user = db.UserProperty(required=True)
    nickname = db.StringProperty(required=False)
    email = db.StringProperty(required=False)

    date_joined = db.DateTimeProperty(auto_now_add=True)
    date_lastlogin = db.DateTimeProperty(auto_now_add=True)

    # user access levels. 0=default, 1=editor, 2=admin
    level = db.IntegerProperty(default=0)

    karma = db.IntegerProperty(default=0)
    points = db.IntegerProperty(default=0)
    achievements = db.StringListProperty(default=[])

    @staticmethod
    def from_user(user):
        if not user:
            return None

        # Valid user, now lets see if we have a userpref object in the db
        q = db.GqlQuery("SELECT * FROM UserPrefs WHERE user = :1", user)
        prefs = q.get()
        if not prefs:
            # First time for this user, create userpref object now
            prefs = UserPrefs(user=user, nickname=user.nickname(), \
                        email=user.email())
            prefs.put()
        return prefs


class Snippet(db.Model):
    """Representation of a snippet (without content). All votes point to this
    snippet, whereas one snippet can have multiple revisions of content
    (community wiki style)."""

    # non-changing attributes
    submitter = db.UserProperty(required=True)
    date_submission = db.DateTimeProperty(auto_now_add=True)

    # default revision reference. of many content revisions any can be default.
    revision = db.IntegerProperty(default=0)


class SnippetUpvote(db.Model):
    """Vote on a snippet"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)


class SnippetComment(db.Model):
    """Comment on a snippet"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(Snippet, required=True)

    date_submission = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now_add=True)
    edits_count = db.IntegerProperty(default=0)

    comment = db.StringProperty(required=False)


class SnippetRevision(db.Model):
    """Content revision of a snippet. If new suggestion by another dev, it is
    held in  moderation until approved."""
    snippet = db.ReferenceProperty(Snippet, required=True)
    contributor = db.UserProperty(required=True)
    date = db.DateTimeProperty(auto_now_add=True)

    # version of the content
    revision_id = db.IntegerProperty(default=0)
    approved = db.BooleanProperty(default=False)

    # content attributes
    title = db.StringProperty(required=False)
    description = db.StringProperty(required=False)
    code = db.StringProperty(required=False)
    categories = db.StringListProperty(default=[])
    tags = db.StringListProperty(default=[])


class SnippetRevisionUpvote(db.Model):
    """Vote on a snippet revision held in moderation"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(SnippetRevision, required=True)


class SnippetRevisionComment(db.Model):
    """Comment on a snippet revision which may be held in moderation"""
    user = db.UserProperty(required=True)
    snippet = db.ReferenceProperty(SnippetRevision, required=True)

    date_submission = db.DateTimeProperty(auto_now_add=True)
    date_lastupdate = db.DateTimeProperty(auto_now_add=True)
    edits_count = db.IntegerProperty(default=0)

    comment = db.StringProperty(required=False)
