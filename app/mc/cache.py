import re
from operator import itemgetter

from google.appengine.api import memcache

from models import *


def tags_mostused(force_update=False):
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
