from google.appengine.ext import webapp
from django.template import Node

# get registry, we need it to register our filter later.
register = webapp.template.create_template_register()

android_versions = {
    3: 'Android 1.5+ (API 3)',
    4: 'Android 1.6+ (API 4)',
    7: 'Android 2.1+ (API 7)',
    8: 'Android 2.2+ (API 8)',
}


# template-tag: use with {{ somevar|half }}
# in the handler, before rendering the template, include tags with
#    webapp.template.register_template_library('common.templateaddons')
def showTag(tag):
    # template cannot do {% for x,y in tag %} :/
    tag, cnt = tag
    return """<a href="javascript:_add_tag('%s')">%s</a>
            <small>(%s)</small>""" % (tag, tag, cnt)


def first(l):
    # template cannot do {% for x,y in tag %} :/
    return l[0]


def android_sdk_to_name(sdk):
    if sdk in android_versions:
        return android_versions[sdk]

register.filter(showTag)
register.filter(first)
register.filter(android_sdk_to_name)
