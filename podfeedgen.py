#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import PyRSS2Gen as rss
import os
import sys
import datetime
import convert
from functools import reduce
from os import path
import urllib.parse
import random
port=3000+random.randint(0,10)
print(port)
esc=urllib.parse.quote
# def esc(s):
#     sym = {
#         # "%": '%25',
#         " ": '%20',
#         "<": '%3C',
#         ">": '%3E',
#         "#": '%23',

#         "{": '%7B',
#         "}": '%7D',
#         '|': '%7C',
#         '\\': '%5C',
#         '^': '%5E',
#         '~': '%7E',
#         '[': '%5B',
#         ']': '%5D',
#         '`': '%60',
#         ';': '%3B',
#         '/': '%2F',
#         '?': '%3F',
#         ':': '%3A',
#         '@': '%40',
#         '=': '%3D',
#         '&': '%26',
#         '$': '%24',
#     }

#     for i in sym:
#         s = s.replace(i, sym[i])
#     return s


def _cmp(x):
    import re
    if len(re.findall(r'.*?(\d+).*(.mp3|.m4v|.M4V|.mp4|.MP4|.mov)$', x)) == 0:
        return 0
    else:
        return int(re.findall(r'.*?(\d+).*(.mp3|.m4v|.M4V|.mp4|.MP4|.mov)$', x)[0][0])


dir = sys.argv[1]
print(os.listdir(dir))
url = sys.argv[2]
myDir = os.path.abspath('.')
os.chdir(dir)
convert.main(dir)
listDir = list(filter(lambda x: path.isdir(x), os.listdir(dir)))
if listDir:
    print(listDir)
    lm = list(map(lambda x: list(map(lambda k: x + '/' + k, os.listdir(x))), listDir))
    print("lm:{}\n *********************".format(lm))
    listDir = reduce(lambda x, y: x + y, lm)
files = list(filter(lambda x: path.splitext(x)[1] in [".MP3",".mp3",".M4V", ".m4v", '.mp4',".MP4", ".mov"], listDir + os.listdir(dir)))
files.sort(key=_cmp)
myItems = [(rss.RSSItem(
    title=n,
    description='',
    enclosure=rss.Enclosure(url+':'+str(port) + '/' + esc(n), 0, "audio/mpeg")
)) for n in files]
myItems.reverse()
feed = rss.RSS2(
    title=path.basename(path.abspath(dir)),
    link="http://unnotigkeit.ya.ru",
    description="",
    lastBuildDate=datetime.datetime.now(),
    items=myItems
)

feed.write_xml(open((dir + '/' + path.basename(path.abspath(dir)) + ".xml"), "w"), "utf-8")
print(url+':'+str(port)+ '/' + esc(path.basename(path.abspath(dir))) + ".xml")
import http.server
os.system('python3 -m http.server {}'.format(port))
