import os
from google.appengine.dist import use_library
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
use_library('django', '1.2')

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

# Load database models
from models import *

# Load request handlers
from handlers import *

urls = [
    (r'/', Main),
    (r'/login', LogIn),
    (r'/_ah/login_required', LogIn),
    (r'/logout', LogOut),

    (r'/add', SnippetsNew),
    (r'/preview', SnippetsNewPreview),

    (r'/tags/([-\w]+)', TagView),

    (r'/profile', ProfileView),
    (r'/authors/(.*)', UserProfileView),

    (r'/admin/x/([-\w]+)', AdminX),
    (r'/admin/y/(.*)', AdminY),
    (r'/admin/del', AdminDel),
    (r'/admin(.*)', AdminView),

    (r'/about(.*)', AboutView),
    (r'/search', SearchView),

    # snippet slug url's at the bottom
    # legacy snippets (301 redirect to slug ones)
    (r'/snippets/([-\w]+)', LegacySnippetView),
    (r'/snippets/([-\w]+)/', LegacySnippetView),
    (r'/snippets/([-\w]+)/index.html', LegacySnippetView),

    # snippets by slug
    (r'/([-\w]+)/vote', SnippetVote),
    (r'/([-\w]+)/edit/([-\w]+)', SnippetEditView),
    (r'/([-\w]+)/edit', SnippetEdit),
    (r'/([-\w]+)/comment', SnippetCommentView),
    (r'/([-\w]+)/index.html', SnippetView),
    (r'/([-\w]+)', SnippetView),
]

application = webapp.WSGIApplication(urls, debug=True)


def profile_main():
    # This is the main function for profiling
    # We've renamed our original main() above to real_main()
    import cProfile
    import pstats
    prof = cProfile.Profile()
    prof = prof.runctx("main()", globals(), locals())
    print "<pre>"
    stats = pstats.Stats(prof)
    stats.sort_stats("time")  # Or cumulative
    stats.print_stats(80)  # 80 = how many to print
    # The rest is optional.
    # stats.print_callees()
    # stats.print_callers()
    print "</pre>"


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
