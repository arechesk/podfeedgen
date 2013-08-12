#!/usr/bin/python
import PyRSS2Gen as rss
import os
from os import path
import sys
import datetime
import operator
from functools import reduce
import urllib2

import convert
dir = sys.argv[1]
print os.listdir(dir)
url = sys.argv[2]
myDir=os.path.abspath('.')
os.chdir(dir)
convert.main(dir)
listDir = filter(lambda x: path.isdir(x), os.listdir(dir))
if listDir!=[]:
    listDir=reduce(lambda x,y: x+y,map(lambda x: map(lambda k:x+'/'+k,os.listdir(x)),listDir))
files = filter(lambda x: path.splitext(x)[1] in [".mp3",".m4v", '.mp4', ".mov"],listDir+ os.listdir(dir))
myItems = [(rss.RSSItem(
    title=n.decode('utf-8'),
    description='',
    enclosure=rss.Enclosure(url + '/' + urllib2.quote(n.decode('utf-8')), 0, "audio/mpeg")
)) for n in files]
feed = rss.RSS2(
    #title=str.decode(path.basename(path.abspath(dir)), 'utf-16'),
    title=path.basename(path.abspath(dir).decode('utf-8')),
    link="http://unnotigkeit.ya.ru",
    description="",
    lastBuildDate=datetime.datetime.now(),
    items=myItems
)
dbpath=os.path.expanduser("~/Dropbox/Public/")
feed.write_xml(open(dir +'/'+ path.basename(path.abspath(dir)) + ".xml", "w"))
print(url + '/' + urllib2.quote(path.basename(path.abspath(dir))) + ".xml")
os.system('python -m SimpleHTTPServer 3000')
os.chdir(myDir)
