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

import httplib2 #Tiene cache. Ver http://httplib2.googlecode.com/hg/doc/html/libhttplib2.html
import json
import xml.etree.ElementTree as ET
import time
import cgi
import ConfigParser
config=ConfigParser.RawConfigParser()
config.read(["/etc/configfile.dat"])
MIAPPKEY=config.get("keys","MIAPPKEY")
PROXYLIST=config.get("keys","PROXYLIST").split(',')
URLCOMMANDVIDEO="https://www.googleapis.com/youtube/v3/videos?id=%s&part=snippet,contentDetails,status,topicDetails,recordingDetails&fields=etag,items(snippet(title,description,categoryId,publishedAt,channelTitle,channelId),contentDetails/caption,contentDetails/duration,status(uploadStatus,license,embeddable),recordingDetails(locationDescription,recordingDate),topicDetails/topicIds)&key=%s"

from mako.lookup import TemplateLookup
from mako import exceptions

root = '/var/ytweb/wsgi-scripts/'

def f_retry(f,*args, **kwargs):
       mtries, mdelay = 4,1 # make mutable
       while mtries > 0:
         try:
           rv = f(*args, **kwargs)
         except:
           rv = [{"status":"500"},""]
         mtries -= 1
         if rv[0]["status"]!= "200" and rv[0]["status"]!='304':  
            time.sleep(mdelay)   #esto  espera tontamente tras el ultimo fallo, es una feature :-D 
         else:
            mtries=0
       return rv

#this idea from http://stackoverflow.com/questions/6893968/how-to-get-the-return-value-from-a-thread-in-python
from threading import Thread
class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs, Verbose)
        self._return = None
    def run(self):
        if self._Thread__target is not None:
            self._return = self._Thread__target(*self._Thread__args,
                                                **self._Thread__kwargs)
    def join(self):
        Thread.join(self)
        return self._return

def doApiHttp(apiHttpObject,apiHttpQuery):
    resp,content=apiHttpObject.request(apiHttpQuery)
    return resp,content

lookup = TemplateLookup(directories=[root, root + 'templates','./'], 
              filesystem_checks=True, 
              module_directory=root+'modules',
              default_filters=['decode.utf8'],
              output_encoding='utf-8', encoding_errors='replace')  #, input_encoding='utf-8')

def serve(environ, start_response):
    videoId=cgi.escape(environ["SCRIPT_URL"].split('/')[2])   #consider re.match for serious control

    if len(videoId) <> 11:
        start_response('404 Not Found',[])
        return ["<body><p>Wrong ID <p> Please extract the ID from youtube URL</body>"]

    parsedQuery=cgi.parse_qs(environ["QUERY_STRING"])

    httplib2.RETRIES=4 #el dfault es 2, no 1!!!
    apihttp=httplib2.Http("/tmp/miAPIcache")  
    import socks
    from random import choice
    #bien hecho faltaria un try-catch para que siga sin proxy
    http=httplib2.Http("/tmp/micache",
            proxy_info=httplib2.ProxyInfo(proxy_type=socks.PROXY_TYPE_HTTP,
            proxy_host=choice(PROXYLIST),
            proxy_rdns=True,
             proxy_port=3128))

    apiThread=ThreadWithReturnValue(target=doApiHttp, args=(apihttp,URLCOMMANDVIDEO % (videoId,MIAPPKEY)))
    apiThread.start()

    import urllib
    import re
    lang,trname,kind="","",""
    resp,contentMainYT=f_retry(http.request,"http://www.youtube.com/watch?v=%s"%videoId)
    #we could parse for #<meta name="keywords" content= too, here
    grepstoryboard=re.search('storyboard_spec...(.[^\"]*.)',contentMainYT)
    regsearch=re.search('TTS_URL.*timedtext.(.*).,',contentMainYT)
    if regsearch is not None:
      ttsurl=urllib.unquote(regsearch.group(1).decode('unicode-escape').replace('\\/','/'))
      respList,contentList=f_retry(http.request,"http://video.google.com/timedtext?"+ttsurl+"&type=list&tlangs=0&asrs=1",headers={'Accept-Language': 'en_US,en_UK,en'})
    else:
      respList,contentList=f_retry(http.request,"http://video.google.com/timedtext?v=%s&type=list"%videoId,headers={'Accept-Language': 'en_US,en_UK,en'})
    if (respList["status"] == "200" or respList["status"] == '304') and len(contentList) > 0: # and len(ET.fromstring(contentList))>0:
                                                  #if (contentInfo["contentDetails"]["caption"]=="true"):
       parsedList=ET.fromstring(contentList)
       if parsedQuery.get('lang')<>None and len(parsedQuery.get('lang'))>0:
         for x in parsedList:
           if x.attrib["lang_code"]==parsedQuery.get('lang')[0]:  #and name, perhaps, in the future
              tmpkind= x.attrib["kind"]  if "kind" in x.attrib and len(x.attrib["kind"])>0 else ""
              tmpQuery= parsedQuery.get('kind')[0] if parsedQuery.get('kind')<> None and len(parsedQuery.get('kind')) >0 else ""
              if tmpkind==tmpQuery:
                    lang=x.attrib["lang_code"]   #si lo tomamos de la query hay que escaparlo con cgi.escape() para evitar ataques 
                    trname=x.attrib["name"]
                    kind=tmpkind
                    break;
         if lang=="": #no hemos conseguido la query, mejor recargamos en la canonica 
            start_response("303 See Other",[('Location','/id/'+videoId),])   #o 302 Found
            return ["<body>no text in the requested language</body"]
       if lang=="":
          for x in parsedList:
                if "kind" in x.attrib: 
                   kind=x.attrib["kind"]  #normalmente asr
                else:
                   kind=""
                lang=x.attrib["lang_code"]  
                trname=x.attrib["name"]
                if "lang_default" in x.attrib:
                   break;
       #ttsurl can get both kinds of request, but really we can just do a straight question if no ASR is needed, so
       #lets keep both methods and see how the API evolves
       if kind=="":
           respTranscript,contentTranscript=f_retry(http.request, 'http://video.google.com/timedtext?lang=%s&v=%s&name=%s'%(lang,videoId,urllib.quote(trname.encode("utf-8"))),"GET")
       else:
           respTranscript,contentTranscript=http.request("http://video.google.com/timedtext?"+ttsurl+"&lang="+lang+"&kind=asr","GET",headers={'Cookie': resp['set-cookie']})
       #print respTranscript
       if len(contentTranscript)<30:
          contentTranscript="<transcript><text start='0.01' dur='2.145'>No text available</text><text>No transcript?</text></transcript>"
       #print contentTranscript
       parsedTranscript=ET.fromstring("<transcript><text start='0.01' dur='2.145'>No text available</text><text>Too long or malformed</text></transcript>")
       try:
          parsedTranscript=ET.fromstring(contentTranscript)
       except:
          pass
    else: 
       parsedList=ET.fromstring("<transcript_list><track note='Empty List'></track></transcript_list>")
       parsedTranscript=ET.fromstring("<transcript><text start='0.01' dur='2.145'>No text available</text><text>Try to reload later</text></transcript>")

    resp,content=apiThread.join()
    if (resp["status"] != "200" and resp["status"] != "304") or len(json.loads(content)["items"])==0:
        if re.search('unavailable-message',contentMainYT):  #buscar unavailable-message
           start_response('410 Gone',[])
           return ["<body>no data now<p> Surely the video has been deleted. Check the video page for more info</body>"]
        else:
           print "Api Failed, we give to 408", resp,content
           start_response('408 Request Timeout',[])   #or 404 Not Found or 410 Gone si queremos que purgue el recurso
           return ["<body>no data now, according YT API<p>Please try again in a few hours</body>"]
    contentInfo=json.loads(content)["items"][0]
    #print contentInfo["status"]
    template=lookup.get_template("comic.html")
    output=template.render(videoInfo=contentInfo["snippet"],videoInfoFull=contentInfo,
                           videoId=videoId,
                           language=lang if lang <> "" else "en",
                           isASR= True if kind=="asr" else False,
                           storyboard_spec=json.loads('"noUrl"' if grepstoryboard == None else grepstoryboard.group(1) ),
                           transcript=parsedTranscript,
                           trList=parsedList)
    response_headers = [('Content-type', 'text/html;charset=UTF-8'),
                        ('Content-Length', str(len(output)))]
    if len(parsedTranscript) < 10 or contentInfo["status"]["license"]<>"creativeCommon": 
       response_headers.append(('robots','noindex,follow'))
       response_headers.append(('X-Robots-Tag','noindex,noarchive,follow,notranslate,noimageindex'))
    else:
       response_headers.append(('X-Robots-Tag','index,follow,notranslate,noimageindex'))
       response_headers.append(('Expires','29 Jun 2014 11:15'))
       response_headers.append(('Cache-control:','public'))
    status = '200 OK'
    start_response(status, response_headers)
    return [output]
 
if __name__ == '__main__':
    port=8000
    import wsgiref.simple_server
    server = wsgiref.simple_server.make_server('', port, serve)
    print "Server listening on port %d" % port
    server.serve_forever()


