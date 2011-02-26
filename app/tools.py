import re
import unicodedata
from operator import itemgetter

from google.appengine.api import memcache

from models import *

_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')


"""Some common tools. All BSD licensed"""


def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    From Django's "django/template/defaultfilters.py".
    """
    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)


def decode(var):
    """Decode form input"""
    if not var:
        return var
    return unicode(var, 'utf-8') if isinstance(var, str) else unicode(var)


def is_valid_email(email):
    if email and len(email) > 7 and re.match( \
        "^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", \
        email):
        return True
    return False


def get_tags_mostused(force_update=False):
    tags = memcache.get("tags_mostused")
    if tags and not force_update:
        return tags

    # Get all tags, build dict with key=name, val=snippet-count
    _tags = Tag.all()
    tags = {}
    for tag in _tags:
        cnt = tag.snippettag_set.count()
        tags[tag.name] = cnt

    # Now sort and take only top 50
    sorted_tags = sorted(tags.iteritems(), key=itemgetter(1), reverse=True)
    sorted_tags = sorted_tags[:100]

    memcache.set("tags_mostused", sorted_tags)
    return sorted_tags
