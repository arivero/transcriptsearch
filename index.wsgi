#!/usr/bin/python
#  Licensed under Affero AGPLv3    
#    Search for videos with captions in youtube 
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

import httplib2
import json
import ConfigParser 
config=ConfigParser.RawConfigParser()
config.read(["/etc/configfile.dat"])
MIAPPKEY=config.get("keys","MIAPPKEY")
URLCOMMAND="https://www.googleapis.com/youtube/v3/search?part=snippet&fields=items(id/videoId,snippet(title,description,thumbnails))&key=%s&maxResults=42&videoCaption=closedCaption&type=video&safeSearch=none&order=date&regionCode=TW"
#order=viewCount, date, relevance, rating 
#import cgi, re, os, posixpath, mimetypes
from mako.lookup import TemplateLookup
from mako import exceptions

root = '/var/ytweb/wsgi-scripts/'
port = 8000
error_style = 'html' # select 'text' for plaintext error reporting

lookup = TemplateLookup(directories=[root, root + 'templates','./'], 
              filesystem_checks=True, 
              module_directory=root+'modules',
              default_filters=['decode.utf8'],
              output_encoding='utf-8', encoding_errors='replace')  #, input_encoding='utf-8')

def serve(environ, start_response):
    http=httplib2.Http()
    headers = {
    #  "GData-Version": "2",
    #  "X-GData-Key": "key=%s" % YOUTUBE_DEVELOPER_KEY
    }
    url=URLCOMMAND % MIAPPKEY
    path=environ.get('PATH_INFO').split('/')
    catname=""
    if path[1]=='m':
       url+="&topicId="+environ.get('PATH_INFO') #it is a freebase topic 
       catname="Freebase Topic "+environ.get('PATH_INFO')
    elif path[1] != "": 
       url+="&videoCategoryId="+path[1]   #it is a youtube category
       catname="Youtube category "+path[1]
    #print url
    resp,content=http.request(url+"&videoLicense=creativeCommon", "GET", headers) 
    # print resp.status
    respuesta=json.loads(content)
    if resp["status"] != "200" or len(respuesta["items"])<5 :
       #if resp["status"] =="200": print len(respuesta["items"]), "items ",
       #print "try again with generic YT license"
       resp,content=http.request(url)
       respuesta=json.loads(content)
    if resp["status"] != "200" or len(respuesta["items"])==0 :
       #print url
       catname=""
       resp,content=http.request(URLCOMMAND % MIAPPKEY)
       respuesta=json.loads(content)
    template=lookup.get_template("index.html")
    status = '200 OK'
    #for entry in respuesta["items"]:
     # print entry["id"]["videoId"]
     # print entry["snippet"]["title"]
     # print entry["snippet"]["description"]
     # print entry["snippet"]["thumbnails"]["default"]["url"]
      #tambien hay medium y high 
    output=template.render(items=respuesta["items"], categoria=catname, enable_loop=True)
    #print len(output)
    response_headers = [('Content-type', 'text/html;charset=UTF-8'),
                        ('Content-Length', str(len(output)))]
    if path[1] != "":
       response_headers.append(('X-Robots-Tag','noarchive,follow,noindex,notranslate,noimageindex'))
    else:
       response_headers.append(('X-Robots-Tag','noarchive,follow,index,notranslate,noimageindex'))
    start_response(status, response_headers)
    return [output]
 
if __name__ == '__main__':
    import wsgiref.simple_server
    server = wsgiref.simple_server.make_server('', port, serve)
    print "Server listening on port %d" % port
    server.serve_forever()


