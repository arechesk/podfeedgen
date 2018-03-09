# PodFeedGen

Podfeedgen - это скрипт для генерации подкаст фида из коллекции мультимедийных файлов.

## How to use
	podfeedgen <dir> <baseUrl>
По умолчанию xml файл сохраняется в папку c файлами.
 Веб-сервер поднимается на локалхосте с 3000 портом. Опускается веб-сервер сочетанием Ctrl+C  
## Example
	podfeedgen . http://127.0.0.1:3000
	
## Requirements
1. OS X или Linux
2. Python 3
3. [PyRSS2Gen](https://pypi.python.org/pypi/PyRSS2Gen)
4. [HandBrakeCLI](http://handbrake.fr/downloads2.php)



## TODO
1. ~~Доделать сортировку~~
2. Доделать парсинг аргументов
3. перейти на flask| Django| Tornado| ... ????????????????????
4. Multiprocessing
5. config ?!?
3. Переписать ReadMe.md
