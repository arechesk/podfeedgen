#!/usr/bin/env python3
"""
Скрипт для создания подкаст-фида (RSS 2.0) из медиафайлов.
При необходимости конвертирует видео других форматов в MP4 с помощью ffmpeg.
Запускает временный HTTP-сервер для раздачи файлов.
"""

import argparse
import datetime
import logging
import mimetypes
import random
import socketserver
import subprocess
import sys
import threading
import urllib.parse
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Расширения, которые считаются готовыми для подкаста (не требуют конвертации)
PODCAST_EXTENSIONS = {'.mp3', '.mp4', '.m4a', '.m4v', '.mov', '.m4b'}

# Расширения, которые будут сконвертированы в MP4
CONVERT_EXTENSIONS = {'.webm', '.avi', '.mkv', '.ogv', '.wmv', '.flv', '.ogg', '.mpg', '.mpeg'}

# MIME типы для RSS enclosure (добавим нужные)
mimetypes.init()
mimetypes.add_type('audio/mpeg', '.mp3')
mimetypes.add_type('audio/mp4', '.m4a')
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/mp4', '.m4v')
mimetypes.add_type('video/quicktime', '.mov')
mimetypes.add_type('audio/x-m4b', '.m4b')


def get_random_available_port(start=3000, end=3010):
    """Возвращает случайный свободный порт из диапазона."""
    import socket
    for _ in range(20):
        port = random.randint(start, end)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Не удалось найти свободный порт в диапазоне {start}-{end}")


def find_files(root_dir: Path, extensions, recursive=True):
    """Возвращает список файлов с заданными расширениями."""
    if recursive:
        return [p for p in root_dir.rglob('*') if p.suffix.lower() in extensions]
    else:
        return [p for p in root_dir.iterdir() if p.is_file() and p.suffix.lower() in extensions]


def convert_with_ffmpeg(input_path: Path, output_path: Path, ffmpeg_path='ffmpeg', codec='copy'):
    """
    Конвертирует файл с помощью ffmpeg.
    По умолчанию копирует потоки (переупаковка). Для перекодирования можно изменить кодек.
    """
    cmd = [ffmpeg_path, '-i', str(input_path), '-c', codec, str(output_path)]
    logger.info(f"Конвертация: {input_path.name} -> {output_path.name}")
    logger.debug(f"Команда: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка конвертации {input_path}: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error(f"ffmpeg не найден по пути '{ffmpeg_path}'. Установите ffmpeg.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Неожиданная ошибка при конвертации {input_path}: {e}")
        return False


def convert_videos(directory: Path, recursive, delete_source, ffmpeg_path, codec='copy'):
    """Конвертирует все видео из CONVERT_EXTENSIONS в MP4."""
    video_files = find_files(directory, CONVERT_EXTENSIONS, recursive)
    if not video_files:
        logger.info("Нет видео для конвертации.")
        return

    logger.info(f"Найдено {len(video_files)} видео для конвертации в MP4.")
    for input_path in video_files:
        output_path = input_path.with_suffix('.mp4')
        if output_path.exists():
            logger.warning(f"Выходной файл уже существует, пропускаем: {output_path}")
            continue

        if convert_with_ffmpeg(input_path, output_path, ffmpeg_path, codec):
            if delete_source:
                try:
                    input_path.unlink()
                    logger.info(f"Исходный файл удалён: {input_path}")
                except Exception as e:
                    logger.error(f"Не удалось удалить {input_path}: {e}")
        else:
            logger.error(f"Конвертация не удалась: {input_path}")


def extract_number(filename: str) -> int:
    """Извлекает первое число из имени файла для сортировки."""
    import re
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else 0


def generate_rss(title, link, description, items, last_build_date):
    """
    Генерирует RSS 2.0 ленту.
    items: список словарей с ключами 'title', 'enclosure_url', 'enclosure_type', 'enclosure_length'
    """
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')

    ET.SubElement(channel, 'title').text = title
    ET.SubElement(channel, 'link').text = link
    ET.SubElement(channel, 'description').text = description
    ET.SubElement(channel, 'lastBuildDate').text = last_build_date.strftime('%a, %d %b %Y %H:%M:%S %z')

    for item_data in items:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = item_data['title']
        enclosure = ET.SubElement(item, 'enclosure')
        enclosure.set('url', item_data['enclosure_url'])
        enclosure.set('length', str(item_data['enclosure_length']))
        enclosure.set('type', item_data['enclosure_type'])

    # Преобразуем в красивый XML
    rough_string = ET.tostring(rss, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def start_http_server(directory: Path, port: int):
    """Запускает HTTP-сервер в отдельном потоке."""
    import http.server
    handler = http.server.SimpleHTTPRequestHandler
    # Меняем текущую директорию на целевую
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(directory)
        with socketserver.TCPServer(("", port), handler) as httpd:
            logger.info(f"HTTP-сервер запущен на порту {port}, раздаёт файлы из {directory}")
            httpd.serve_forever()
    except Exception as e:
        logger.error(f"Ошибка при запуске сервера: {e}")
    finally:
        os.chdir(original_cwd)


def main():
    parser = argparse.ArgumentParser(
        description="Создаёт подкаст-фид из медиафайлов, при необходимости конвертирует видео в MP4, запускает веб-сервер."
    )
    parser.add_argument('directory', help="Директория с медиафайлами")
    parser.add_argument('base_url', help="Базовый URL (например, http://localhost)")
    parser.add_argument('--port', type=int, help="Порт для сервера (если не указан, выбирается случайный)")
    parser.add_argument('--no-convert', action='store_true', help="Не выполнять конвертацию видео")
    parser.add_argument('--delete-source', action='store_true', help="Удалять исходные файлы после конвертации")
    parser.add_argument('--no-recursive', action='store_true', help="Не обрабатывать поддиректории")
    parser.add_argument('--ffmpeg-path', default='ffmpeg', help="Путь к ffmpeg")
    parser.add_argument('--codec', default='copy', help="Кодек для конвертации (copy или libx264 и т.д.)")
    parser.add_argument('--verbose', action='store_true', help="Подробный вывод")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    media_dir = Path(args.directory).resolve()
    if not media_dir.is_dir():
        logger.error(f"Директория не существует: {media_dir}")
        sys.exit(1)

    base_url = args.base_url.rstrip('/')
    recursive = not args.no_recursive

    # 1. Конвертация видео, если нужно
    if not args.no_convert:
        convert_videos(media_dir, recursive, args.delete_source, args.ffmpeg_path, args.codec)

    # 2. Сбор медиафайлов для подкаста
    media_files = find_files(media_dir, PODCAST_EXTENSIONS, recursive)
    if not media_files:
        logger.error("Не найдено медиафайлов для подкаста.")
        sys.exit(1)
    logger.info(f"Найдено {len(media_files)} медиафайлов.")

    # 3. Сортировка по числу в имени (обратный порядок)
    media_files.sort(key=lambda p: extract_number(p.name), reverse=True)

    # 4. Выбор порта
    if args.port:
        port = args.port
    else:
        try:
            port = get_random_available_port()
        except RuntimeError as e:
            logger.error(e)
            sys.exit(1)

    # 5. Формирование RSS элементов
    items = []
    for file_path in media_files:
        rel_path = file_path.relative_to(media_dir).as_posix()
        file_url = urllib.parse.urljoin(base_url, f"{port}/{urllib.parse.quote(rel_path)}")
        mime_type, _ = mimetypes.guess_type(file_path.name)
        if not mime_type:
            mime_type = "application/octet-stream"
        size = file_path.stat().st_size
        items.append({
            'title': file_path.name,
            'enclosure_url': file_url,
            'enclosure_length': size,
            'enclosure_type': mime_type,
        })

    # 6. Генерация RSS
    feed_title = media_dir.name
    feed_link = base_url
    rss_xml = generate_rss(
        title=feed_title,
        link=feed_link,
        description="",
        items=items,
        last_build_date=datetime.datetime.now().astimezone()
    )

    # 7. Сохранение RSS в файл
    xml_filename = media_dir / f"{feed_title}.xml"
    try:
        with open(xml_filename, 'w', encoding='utf-8') as f:
            f.write(rss_xml)
        logger.info(f"RSS сохранён: {xml_filename}")
    except Exception as e:
        logger.error(f"Ошибка записи RSS: {e}")
        sys.exit(1)

    # 8. Вывод URL
    rss_url = urllib.parse.urljoin(base_url, f"{port}/{xml_filename.name}")
    print(f"RSS URL: {rss_url}")

    # 9. Запуск HTTP-сервера в фоне
    server_thread = threading.Thread(target=start_http_server, args=(media_dir, port), daemon=True)
    server_thread.start()
    logger.info("Сервер запущен. Нажмите Ctrl+C для остановки.")
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        logger.info("Остановка.")


if __name__ == '__main__':
    main()
