#__author__ = 'alex'
#python -m SimpleHTTPServe
#parse argv
#real time
#recursive
#convert avi->mp4
#web-interface
#port js,ruby
import PyRSS2Gen as rss
import os
from os import path
import sys
import datetime

dir = sys.argv[1]
url = sys.argv[2]
listDir = filter(lambda x: path.isdir(x), os.listdir(dir))
if listDir!=[]:
    listDir=reduce(lambda x,y: x+y,map(lambda x: map(lambda k:x+'/'+k,os.listdir(x)),listDir))
files = filter(lambda x: path.splitext(x)[1] in [".mp3", '.mp4', ".mov"],listDir+ os.listdir(dir))
myItems = [(rss.RSSItem(
    title=n,
    description='',
    enclosure=rss.Enclosure((url + '/' + n).replace(' ','%20'), 0, "audio/mpeg")
)) for n in files]
feed = rss.RSS2(
    title=str.decode(path.basename(path.abspath(dir)), 'utf-8'),
    link="http://unnotigkeit.ya.ru",
    description="",
    lastBuildDate=datetime.datetime.now(),
    items=myItems
)
feed.write_xml(open("/Users/alex/Dropbox/Public/" + path.basename(path.abspath(dir)) + ".xml", "w"))
os.system('python -m SimpleHTTPServer 3000')
print(files)
