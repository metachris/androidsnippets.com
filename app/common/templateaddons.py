from google.appengine.ext import webapp
from django.template import Node

# get registry, we need it to register our filter later.
register = webapp.template.create_template_register()


# template-tag: use with {{ somevar|half }}
# in the handler, before rendering the template, include tags with
#    webapp.template.register_template_library('common.templateaddons')
def showTag(tag):
    # template cannot do {% for x,y in tag %} :/
    tag, cnt = tag
    return """<a href="javascript:_add_tag('%s')">%s</a>
            <small>(%s)</small>""" % (tag, tag, cnt)

register.filter(showTag)
