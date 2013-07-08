#!/usr/bin/python
#  Licensed under Affero AGPLv3    
#    Shows captions from yt in a comic-like format 
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

import httplib2 #Tiene cache. Ver http://httplib2.googlecode.com/hg/doc/html/libhttplib2.html
import json
import xml.etree.ElementTree as ET
import time
import ConfigParser
config=ConfigParser.RawConfigParser()
config.read(["/etc/configfile.dat"])
MIAPPKEY=config.get("keys","MIAPPKEY")
URLCOMMANDVIDEO="https://www.googleapis.com/youtube/v3/videos?id=%s&part=snippet,contentDetails,topicDetails,recordingDetails&fields=etag,items(snippet(title,description,categoryId),contentDetails/caption,contentDetails/duration,recordingDetails(locationDescription,recordingDate),topicDetails/topicIds)&key=%s"

from mako.lookup import TemplateLookup
from mako import exceptions

root = '/var/ytweb/wsgi-scripts/'
port = 8000
error_style = 'html' # select 'text' for plaintext error reporting


def f_retry(f,*args, **kwargs):
       mtries, mdelay = 4,1 # make mutable
       while mtries > 0:
         rv = f(*args, **kwargs)
         mtries -= 1
         if rv[0]["status"]!= "200" and rv[0]["status"]!='304':  
            time.sleep(mdelay)   #esto  espera tontamente tras el ultimo fallo, es una feature :-D 
         else:
            mtries=0
       return rv


lookup = TemplateLookup(directories=[root, root + 'templates','./'], 
              filesystem_checks=True, 
              module_directory=root+'modules',
              default_filters=['decode.utf8'],
              output_encoding='utf-8', encoding_errors='replace')  #, input_encoding='utf-8')

def serve(environ, start_response):

    videoId=environ["REQUEST_URI"].split('/')[2]

    http=httplib2.Http("/tmp/micache") # con .cache? 
    headers = { } 
    resp,content=f_retry(http.request,URLCOMMANDVIDEO % (videoId,MIAPPKEY), "GET")
    if resp["status"] != "200" and resp["status"] != "304":
        start_response('404 Not Found',[])
        return ["<body>no data now<p>Please try again in a few seconds... </body>"]
    contentItems=json.loads(content)["items"]
    if len(contentItems)>0:
       contentInfo=contentItems[0]
    else:
       start_response('404 Not Found',[])
       return ["<body>no data now<p>Please try again in a few seconds </body>"]

    parsedTranscript=ET.fromstring("<transcript><text start='0.01' dur='2.145'>No text available</text><text>Try to reload later</text></transcript>")
    parsedList=ET.fromstring("<transcript_list><track note='Uncaptioned Video'></track></transcript_list>") 
    import urllib
    import re
    resp,contentMainYT=f_retry(http.request,"http://www.youtube.com/watch?v=%s"%videoId)
    #we could parse for #<meta name="keywords" content= too, here
    grepstoryboard=re.search('storyboard_spec...(.[^\"]*.)',contentMainYT)
    #print json.loads(grepstoryboard.group(1))
    lang="en"
    if (contentInfo["contentDetails"]["caption"]=="true"):
       trname=""
       parsedList=ET.fromstring("<transcript_list><track note='Empty List'></track></transcript_list>")
       respList,contentList=f_retry(http.request,"http://video.google.com/timedtext?v=%s&type=list"%videoId,"GET")
       if respList["status"] == "200" or respList["status"] == '304':
          if len(contentList) > 0:
             parsedList=ET.fromstring(contentList)
             for x in parsedList:
                if "lang_default" in x.attrib: 
                     lang=x.attrib["lang_code"]  
                     trname=x.attrib["name"]
                     break    
                if "lang_code" in x.attrib: lang=x.attrib["lang_code"]
                if "name"  in x.attrib: trname=x.attrib["name"]
             #rname=trname.encode("utf-8").decode("unicode-escape") #encode("utf-8")
             #print lang, videoId, trname
             #print lcode,lang,trname
       respTranscript,contentTranscript=f_retry(http.request,
             'http://video.google.com/timedtext?lang=%s&v=%s&name=%s'%(lang,videoId,urllib.quote(trname.encode("utf-8"))),"GET")
       if respTranscript["status"] == "200" or respList["status"] == '304':
          if len(contentTranscript) > 0:
             parsedTranscript=ET.fromstring(contentTranscript)
    else: #try to extract the automatic caption #compare with http://code.google.com/p/youtubexbmc/source/browse/branches/release/YouTubePlayer.py?r=978
       regsearch=re.search('TTS_URL.*timedtext.(.*).,',contentMainYT)
       if regsearch is not None: 
          ttsurl=urllib.unquote(regsearch.group(1).decode('unicode-escape').replace('\\/','/'))
          parsedList=ET.fromstring("<transcript_list><track note='Got only automatic transcription'></track></transcript_list>")
          respList,contentList=f_retry(http.request,"http://video.google.com/timedtext?"+ttsurl+"&type=list&tlangs=0&asrs=1")
          if respList["status"] == "200" or respList["status"] == '304':
            if len(contentList) > 0:
               parsedList=ET.fromstring(contentList)
               for x in parsedList:
                  if "lang_code" in x.attrib: lang=x.attrib["lang_code"]
          respTranscript,contentTranscript=http.request("http://video.google.com/timedtext?"+ttsurl+"&lang="+lang+"&kind=asr","GET",headers={'Cookie': resp['set-cookie']})
          if len(contentTranscript) > 0:
              parsedTranscript=ET.fromstring(contentTranscript)
    

    template=lookup.get_template("comic.html")
    output=template.render(videoInfo=contentInfo["snippet"],videoInfoFull=contentInfo,
                           videoId=videoId,
                           storyboard_spec=json.loads('"noUrl"' if grepstoryboard == None else grepstoryboard.group(1) ),
                           transcript=parsedTranscript,
                           trList=parsedList)
    response_headers = [('Content-type', 'text/html;charset=UTF-8'),
                        ('Content-Length', str(len(output)))]
    status = '200 OK'
    start_response(status, response_headers)
    return [output]
 
if __name__ == '__main__':
    import wsgiref.simple_server
    server = wsgiref.simple_server.make_server('', port, serve)
    print "Server listening on port %d" % port
    server.serve_forever()


