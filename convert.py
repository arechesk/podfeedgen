#!/usr/bin/python
import os
from os import path
import sys

def main(curDir=path.abspath('.')):
	for i in filter(lambda x: path.isdir(x), os.listdir(curDir)):
		for j in filter(lambda x: path.splitext(x)[1] in ['.webm','.avi','.mpg','.mkv','.ogv','.wmv','.flv','.ogg'],os.listdir(i)):
			os.system('HandBrakeCLI -i "./'+i+'/'+j+'" -o "./'+i+'/'+path.splitext(j)[0]+'.mov"')
			os.system('rm -f "./'+i+'/'+j+'"')
	listDir = filter(lambda x: path.splitext(x)[1] in ['.m4v','.webm','.FLV','.avi','.mpg','.ogv','.mkv', '.wmv', '.flv','.ogg'], os.listdir(curDir))
	print (os.listdir(curDir))
	for i in listDir:
		os.system('HandBrakeCLI -i "' + i + '" -o "' + path.splitext(i)[0] + '.mov"')
		os.system('rm -f "' + i + '"')

if '__main__'==__name__:
	if sys.argv.__len__()==1:
		main()
	else:
		main(sys.argv[1])
