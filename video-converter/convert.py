#__author__ = 'alex'
import os
from os import path


def main(curDir=path.abspath('.')):
    for i in filter(lambda x: path.isdir(x), os.listdir(curDir)):
	    for j in filter(lambda x: path.splitext(x)[1] in ['.avi','.wmv','.flv'],os.listdir(i)):
		    os.system('HandBrakeCLI -i "./'+i+'/'+j+'" -o "./'+i+'/'+path.splitext(j)[0]+'.mp4"')
		    os.system('rm -f "./'+i+'/'+j+'"')
    listDir = filter(lambda x: path.splitext(x)[1] in ['.avi', '.wmv', '.flv'], os.listdir(curDir))

    for i in listDir:
        os.system('HandBrakeCLI -i "' + i + '" -o "' + path.splitext(i)[0] + '.mp4"')
        os.system('rm -f "' + i + '"')

main()
