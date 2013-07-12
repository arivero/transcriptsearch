transcriptsearch
================

Create transcripts of youtube, and perhaps other online services

See it working at www.transcriptsearch.com.es

The main idea of this set of scripts is to offer a search engine for
youtube transcription. We are agnostics about the spider; in this
simple case we just offer a sitemap to google custom engine, and
let it to do the crawl. You could also use Yacy, or perhaps
a python based crawler and search engine.


-------------------------

The scripts are made to work with apache WSGIa module.
You must provide executions for /id, /comic and / :

    WSGIScriptAlias /id /cript/video.wsgi
    WSGIScriptAlias /comic /cript/comic.wsgi
    WSGIScriptAlias / /cript/index.wsgi

The main worry for installation is to be sure that you have
all the needed modules for python and the webserver. If
you do implementations using other libraries (eg, getting 
rid of httplib2), please honor the AGPLv3, it is so easy
as branching it here in github :-D

You must also provide a configfile with  your youtube API key
and a comma separated list of proxies. That, or edit the
proxy code out.

--------------------------

If you plan to use this idea as a service, you should consider
Youtube terms and conditions. Particularly, under 5.3, 
you should not cache the contents of a crawl, so you should
disable the cache feature in httplib2 for the "video.wsgi" page 
or purge it frequently. Surely the license of google about
youtube contents is different, so you can consider to allow 
them to kept the cache. You can also consider to "redirect 30x"
directly to youtube.com, but googlebot does not like extensive
use of redirections.  

Neither the video.wsgi script nor the comic.wsgi are replaying
the video, so most of the issues about independent players
do not apply. But comic.wsgi can be considered a rework
of the original work; you are in safer grounds if you only
allow comic.wsgi for videos with Creative Commons license. The
videos under general youtube license also allow for 
reworking, but the wording of the license is more convolved
and it only applies while the video still exists in youtube.

You can also consider to offer the original Youtube Player
in the result pages, but I am not sure if in such case you
go away from the search aid approach and you wander 
towards a typical youtube scraper clone.

In any case, do not take my words as legal advice; it is
simply a guide for you to understand that there are issues
always when you plan an internet search aid. You must consider
your local rules, and you can also consider Google's BCP:
as they are both the owners of Youtube and of the Dominant
Search Engine in the web, their commom practices are surely
the most valid practices.

