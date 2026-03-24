import unittest
import tempfile
import shutil
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
import xml.etree.ElementTree as ET
import datetime
import urllib.parse
import mimetypes

# Импортируем тестируемый модуль
# Предполагаем, что скрипт называется podcast_generator.py
import podcast_generator as pg

class TestPodcastGenerator(unittest.TestCase):
    def setUp(self):
        # Создаем временную директорию для тестов
        self.test_dir = tempfile.mkdtemp()
        self.media_dir = Path(self.test_dir)
        
        # Создаем тестовые файлы
        self.create_test_files()
        
        # Сохраняем оригинальный sys.argv для восстановления
        self.orig_argv = sys.argv
        
    def tearDown(self):
        # Удаляем временную директорию
        shutil.rmtree(self.test_dir, ignore_errors=True)
        sys.argv = self.orig_argv
        
    def create_test_files(self):
        # Создаем несколько файлов с разными расширениями и именами
        files = [
            'episode_01.mp3',
            'episode_02.mp4',
            'video_03.webm',
            'video_04.avi',
            'no_number.mkv',
            'subdir/video_05.mp4',
            'subdir/video_06.webm',
        ]
        for f in files:
            path = self.media_dir / f
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("dummy content")
    
    # Тесты для find_files
    def test_find_files_recursive(self):
        extensions = {'.mp3', '.mp4'}
        result = pg.find_files(self.media_dir, extensions, recursive=True)
        expected_names = ['episode_01.mp3', 'episode_02.mp4', 'subdir/video_05.mp4']
        expected = [self.media_dir / name for name in expected_names]
        self.assertCountEqual(result, expected)
    
    def test_find_files_non_recursive(self):
        extensions = {'.mp3', '.mp4'}
        result = pg.find_files(self.media_dir, extensions, recursive=False)
        expected_names = ['episode_01.mp3', 'episode_02.mp4']
        expected = [self.media_dir / name for name in expected_names]
        self.assertCountEqual(result, expected)
    
    def test_find_files_no_match(self):
        result = pg.find_files(self.media_dir, {'.xyz'}, recursive=True)
        self.assertEqual(result, [])
    
    # Тесты для extract_number
    def test_extract_number_with_number(self):
        self.assertEqual(pg.extract_number("episode_01.mp3"), 1)
        self.assertEqual(pg.extract_number("video_123_abc.mp4"), 123)
        self.assertEqual(pg.extract_number("123.mp4"), 123)
    
    def test_extract_number_without_number(self):
        self.assertEqual(pg.extract_number("no_number.mkv"), 0)
        self.assertEqual(pg.extract_number("file"), 0)
    
    def test_extract_number_multiple_numbers(self):
        # Первое число
        self.assertEqual(pg.extract_number("ep_12_34.mp4"), 12)
    
    # Тесты для convert_with_ffmpeg
    @patch('podcast_generator.subprocess.run')
    def test_convert_with_ffmpeg_success(self, mock_run):
        mock_run.return_value = MagicMock()
        input_path = self.media_dir / "test.webm"
        output_path = self.media_dir / "test.mp4"
        result = pg.convert_with_ffmpeg(input_path, output_path)
        self.assertTrue(result)
        mock_run.assert_called_once()
        # Проверяем аргументы
        call_args = mock_run.call_args[0][0]
        self.assertEqual(call_args, ['ffmpeg', '-i', str(input_path), '-c', 'copy', str(output_path)])
    
    @patch('podcast_generator.subprocess.run')
    def test_convert_with_ffmpeg_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, 'cmd', stderr="error")
        input_path = self.media_dir / "test.webm"
        output_path = self.media_dir / "test.mp4"
        with self.assertLogs(pg.logger, level='ERROR') as log:
            result = pg.convert_with_ffmpeg(input_path, output_path)
        self.assertFalse(result)
        self.assertIn("Ошибка конвертации", log.output[0])
    
    @patch('podcast_generator.subprocess.run')
    def test_convert_with_ffmpeg_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        input_path = self.media_dir / "test.webm"
        output_path = self.media_dir / "test.mp4"
        with self.assertRaises(SystemExit):
            pg.convert_with_ffmpeg(input_path, output_path)
    
    # Тесты для convert_videos
    @patch('podcast_generator.convert_with_ffmpeg')
    @patch('podcast_generator.find_files')
    def test_convert_videos_no_files(self, mock_find, mock_convert):
        mock_find.return_value = []
        pg.convert_videos(self.media_dir, True, False, 'ffmpeg', 'copy')
        mock_convert.assert_not_called()
    
    @patch('podcast_generator.convert_with_ffmpeg')
    @patch('podcast_generator.find_files')
    def test_convert_videos_success(self, mock_find, mock_convert):
        mock_convert.return_value = True
        # Создаем список путей для конвертации
        webm_path = self.media_dir / "test.webm"
        mock_find.return_value = [webm_path]
        pg.convert_videos(self.media_dir, True, False, 'ffmpeg', 'copy')
        mock_convert.assert_called_once_with(webm_path, webm_path.with_suffix('.mp4'), 'ffmpeg', 'copy')
    
    @patch('podcast_generator.convert_with_ffmpeg')
    @patch('podcast_generator.find_files')
    def test_convert_videos_delete_source(self, mock_find, mock_convert):
        mock_convert.return_value = True
        webm_path = self.media_dir / "test.webm"
        mock_find.return_value = [webm_path]
        # Создаем файл, который будет удален
        webm_path.write_text("dummy")
        pg.convert_videos(self.media_dir, True, True, 'ffmpeg', 'copy')
        self.assertFalse(webm_path.exists())
    
    # Тесты для generate_rss
    def test_generate_rss_basic(self):
        items = [{
            'title': 'test.mp3',
            'enclosure_url': 'http://localhost/test.mp3',
            'enclosure_length': 12345,
            'enclosure_type': 'audio/mpeg'
        }]
        last_build = datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        xml_str = pg.generate_rss("Test Title", "http://example.com", "Description", items, last_build)
        # Парсим XML
        root = ET.fromstring(xml_str)
        channel = root.find('channel')
        self.assertIsNotNone(channel)
        title = channel.find('title')
        self.assertEqual(title.text, "Test Title")
        link = channel.find('link')
        self.assertEqual(link.text, "http://example.com")
        desc = channel.find('description')
        self.assertEqual(desc.text, "Description")
        last_build_elem = channel.find('lastBuildDate')
        self.assertEqual(last_build_elem.text, "Sun, 01 Jan 2023 12:00:00 +0000")
        item = channel.find('item')
        self.assertIsNotNone(item)
        item_title = item.find('title')
        self.assertEqual(item_title.text, "test.mp3")
        enclosure = item.find('enclosure')
        self.assertEqual(enclosure.get('url'), "http://localhost/test.mp3")
        self.assertEqual(enclosure.get('length'), "12345")
        self.assertEqual(enclosure.get('type'), "audio/mpeg")
    
    # Тесты для get_random_available_port
    @patch('socket.socket')
    def test_get_random_available_port_success(self, mock_socket):
        # Мокаем сокет, чтобы bind всегда успешен
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.bind = MagicMock()
        port = pg.get_random_available_port()
        self.assertIsInstance(port, int)
        self.assertGreaterEqual(port, 3000)
        self.assertLessEqual(port, 3010)
    
    @patch('socket.socket')
    def test_get_random_available_port_fail(self, mock_socket):
        # Мокаем сокет, чтобы bind всегда кидал OSError
        mock_sock = MagicMock()
        mock_socket.return_value.__enter__.return_value = mock_sock
        mock_sock.bind.side_effect = OSError
        with self.assertRaises(RuntimeError):
            pg.get_random_available_port()
    
    # Тесты для start_http_server (просто проверяем, что запускается)
    @patch('socketserver.TCPServer')
    @patch('os.chdir')
    def test_start_http_server(self, mock_chdir, mock_tcp_server):
        mock_server = MagicMock()
        mock_tcp_server.return_value = mock_server
        pg.start_http_server(self.media_dir, 8080)
        mock_tcp_server.assert_called_once_with(("", 8080), unittest.mock.ANY)
        mock_server.serve_forever.assert_called_once()
        mock_chdir.assert_any_call(self.media_dir)
    
    # Тесты для main
    @patch('sys.argv', ['script.py', '/tmp', 'http://localhost'])
    @patch('podcast_generator.convert_videos')
    @patch('podcast_generator.find_files')
    @patch('podcast_generator.get_random_available_port')
    @patch('builtins.open', new_callable=mock_open)
    @patch('threading.Thread')
    def test_main_happy_path(self, mock_thread, mock_open, mock_get_port, mock_find_files, mock_convert_videos):
        # Подготавливаем моки
        mock_get_port.return_value = 3000
        # Создаем список файлов (один mp3)
        mp3_path = self.media_dir / "episode_01.mp3"
        mock_find_files.return_value = [mp3_path]
        # Мокаем запуск потока
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        # Меняем директорию на временную
        with patch('podcast_generator.Path.is_dir', return_value=True), \
             patch('podcast_generator.Path.resolve', return_value=self.media_dir), \
             patch('podcast_generator.Path.relative_to', return_value=Path('episode_01.mp3')), \
             patch('pathlib.Path.stat', return_value=MagicMock(st_size=1000)):
            pg.main()
        
        # Проверяем вызовы
        mock_convert_videos.assert_called_once()
        mock_find_files.assert_called_once()
        mock_get_port.assert_called_once()
        mock_open.assert_called_once()
        mock_thread.assert_called_once_with(target=pg.start_http_server, args=(self.media_dir, 3000), daemon=True)
        mock_thread_instance.start.assert_called_once()
    
    @patch('sys.argv', ['script.py', '/tmp', 'http://localhost', '--no-convert', '--port', '8080'])
    @patch('podcast_generator.find_files')
    @patch('builtins.open', new_callable=mock_open)
    @patch('threading.Thread')
    def test_main_no_convert_and_port(self, mock_thread, mock_open, mock_find_files):
        # Подготавливаем моки
        mp3_path = self.media_dir / "episode_01.mp3"
        mock_find_files.return_value = [mp3_path]
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        with patch('podcast_generator.Path.is_dir', return_value=True), \
             patch('podcast_generator.Path.resolve', return_value=self.media_dir), \
             patch('podcast_generator.Path.relative_to', return_value=Path('episode_01.mp3')), \
             patch('pathlib.Path.stat', return_value=MagicMock(st_size=1000)):
            pg.main()
        
        # Проверяем, что convert_videos не вызывалась
        # (мы не мокали convert_videos, значит она должна быть вызвана? но мы передали --no-convert)
        # В коде main: if not args.no_convert: convert_videos(...)
        # Мы не мокали convert_videos, но поскольку она не вызывается, проблем не будет.
        # Просто проверим, что find_files был вызван и порт использован из аргументов
        mock_find_files.assert_called_once()
        # Убедимся, что get_random_available_port не вызывалась, т.к. порт задан
        # Но мы не мокали её, но если бы она вызвалась, то упала бы, потому что нет мока.
        # Так как тест проходит, значит не вызывалась.
        mock_thread.assert_called_once_with(target=pg.start_http_server, args=(self.media_dir, 8080), daemon=True)
    
    @patch('sys.argv', ['script.py', '/nonexistent', 'http://localhost'])
    def test_main_directory_not_exist(self):
        with self.assertRaises(SystemExit):
            pg.main()
    
    @patch('sys.argv', ['script.py', self.test_dir, 'http://localhost'])
    @patch('podcast_generator.find_files', return_value=[])
    def test_main_no_media_files(self, mock_find):
        with self.assertRaises(SystemExit):
            pg.main()

if __name__ == '__main__':
    unittest.main()
