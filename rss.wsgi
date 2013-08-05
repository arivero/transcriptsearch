#!/usr/bin/python
#  Licensed under Affero AGPLv3    
#    Shows captions from yt  
#    Copyright (C) 2013 A. Rivero
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import anydbm
import pickle
import cgi

def serve(environ, start_response):
    output=[]
    output.append('<?xml version="1.0" encoding="UTF-8" ?>')
    output.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n')
    output.append('<channel>'+
           '<title>Recent</title>'+
           '<description>Recently visited</description>'+
           '<atom:link href="http://www.transcriptsearch.com.es/recent.rss" rel="self" type="application/rss+xml" />'+
           '<link>http://www.transcriptsearch.com.es/recent.rss</link>\n')
    db = anydbm.open('/tmp/recentVisits', 'r')
    for k, v in db.iteritems():
        data=pickle.loads(v)
        output.append("<item>\n")
        output.append("<title>"+cgi.escape(data["title"])+"</title>\n")
        output.append("<description>"+cgi.escape(data["desc"])+"</description>\n")
        output.append("<link>http://www.transcriptsearch.com.es/id/"+data["id"]+"</link>\n") 
        output.append('<guid isPermaLink="false">'+data["id"]+"</guid>\n")  
        output.append("</item>\n")
    output.append('</channel>\n')
    output.append('</rss>\n')
    response_headers = [('Content-type', 'application/rss+xml;charset=UTF-8'),
                        ]
    status = '200 OK'
    start_response(status, response_headers)
    return [x.encode("UTF-8") for x in output]
 
if __name__ == '__main__':
    port=8000
    import wsgiref.simple_server
    server = wsgiref.simple_server.make_server('', port, serve)
    print "Server listening on port %d" % port
    server.serve_forever()


