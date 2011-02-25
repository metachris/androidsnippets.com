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
    (r'/account', Account),

    (r'/add', SnippetsNew),
    (r'/preview', SnippetsNewPreview),

    (r'/tags/([-\w]+)', TagView),

    (r'/profile', ProfileView),
    (r'/authors/(.*)', UserProfileView),

    (r'/admin/x', AdminX),

    # snippet slug url's at the bottom
    (r'/snippets/([-\w]+)', LegacySnippetView),
    (r'/([-\w]+)/vote', SnippetVote),
    (r'/([-\w]+)/edit/([-\w]+)', SnippetEditView),
    (r'/([-\w]+)/edit', SnippetEdit),
    (r'/([-\w]+)/comment', SnippetCommentView),
    (r'/([-\w]+)', SnippetView),

]

application = webapp.WSGIApplication(urls, debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
