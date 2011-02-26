from google.appengine.ext import webapp
from django.template import Node

"""
http://docs.djangoproject.com/en/dev/howto/custom-template-tags/
"""

# get registry, we need it to register our filter later.
register = webapp.template.create_template_register()

android_versions = {
    3: 'Android 1.5+ (API 3)',
    4: 'Android 1.6+ (API 4)',
    7: 'Android 2.1+ (API 7)',
    8: 'Android 2.2+ (API 8)',
}


def first(l):
    # template cannot do {% for x,y in tag %} :/
    return l[0]


def android_sdk_to_name(sdk):
    if sdk in android_versions:
        return android_versions[sdk]


def is_notification(bitfield, test_bit):
    return "checked='checked'" if bitfield & test_bit == test_bit else ""


def mkSize(val, max):
    """make tag cloud. min=11px, max=17px;"""
    size_maxdelta = 10.0 / float(max)
    return 13.0 + (size_maxdelta * float(val))

register.filter(first)
register.filter(android_sdk_to_name)
register.filter(is_notification)
register.filter(mkSize)
