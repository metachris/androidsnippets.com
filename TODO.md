


New Snippets
-------------

* Read and confirm submit guidelines


Memcache
--------

* Snippet view count


[ ] Appstats: http://code.google.com/appengine/docs/python/tools/appstats.html



Redirect to www (htaccess redirect)

Create a .htaccess file with the below code, it will ensure that all requests coming in to domain.com will get redirected to www.domain.com 
The .htaccess file needs to be placed in the root directory of your old website (i.e the same directory where your index file is placed)

Options +FollowSymlinks
RewriteEngine on
rewritecond %{http_host} ^domain.com [nc]
rewriterule ^(.*)$ http://www.domain.com/$1 [r=301,nc]

Please REPLACE domain.com and www.newdomain.com with your actual domain name.



Redirect Old domain to New domain (htaccess redirect)

Create a .htaccess file with the below code, it will ensure that all your directories and pages of your old domain will get correctly redirected to your new domain.
The .htaccess file needs to be placed in the root directory of your old website (i.e the same directory where your index file is placed)

Options +FollowSymLinks
RewriteEngine on
RewriteRule (.*) http://www.newdomain.com/$1 [R=301,L]

Please REPLACE www.newdomain.com in the above code with your actual domain name.

In addition to the redirect I would suggest that you contact every backlinking site to modify their backlink to point to your new website.

