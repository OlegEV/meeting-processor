#!/usr/bin/env python3
"""
Модуль для обработки файлов по HTTP ссылкам и облачным сервисам
"""

import os
import re
import aiohttp
import asyncio
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from urllib.parse import urlparse, parse_qs, unquote
import tempfile
import logging

logger = logging.getLogger(__name__)

class CloudServiceHandler:
    """Обработчик облачных сервисов"""
    
    @staticmethod
    def is_cloud_url(url: str) -> Tuple[bool, str]:
        """
        Проверяет, является ли URL облачным сервисом
        Returns: (is_cloud, service_name)
        """
        cloud_patterns = {
            'google_drive': [
                r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
                r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
                r'docs\.google\.com/.*/(.*)/edit'
            ],
            'yandex_disk': [
                r'disk\.yandex\.[a-z]+/d/([a-zA-Z0-9_-]+)',
                r'disk\.yandex\.[a-z]+/i/([a-zA-Z0-9_-]+)',
                r'yadi\.sk/[a-zA-Z]/([a-zA-Z0-9_-]+)'
            ]
        }
        
        for service, patterns in cloud_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return True, service
        
        return False, 'direct'
    
    @staticmethod
    def convert_google_drive_url(url: str) -> Optional[str]:
        """Конвертирует Google Drive ссылку в прямую ссылку для скачивания"""
        # Извлекаем ID файла из различных форматов Google Drive URLs
        patterns = [
            r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
            r'docs\.google\.com/.*/([a-zA-Z0-9_-]+)/edit'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                file_id = match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"
        
        return None
    
    @staticmethod
    def convert_yandex_disk_url(url: str) -> Optional[str]:
        """Конвертирует Яндекс.Диск ссылку в прямую ссылку для скачивания"""
        if 'yadi.sk' in url or 'disk.yandex' in url:
            # Для публичных ссылок Яндекс.Диска используем API для получения прямой ссылки
            # Возвращаем URL для дальнейшей обработки через API
            return url
        return None
    
    @staticmethod
    async def get_yandex_disk_download_url(session, public_url: str) -> Optional[str]:
        """Получает прямую ссылку для скачивания с Яндекс.Диска через API"""
        try:
            # API Яндекс.Диска для получения информации о публичном файле
            api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
            params = {"public_key": public_url}
            
            async with session.get(api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("href")
                else:
                    logger.error(f"Ошибка API Яндекс.Диска: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Ошибка получения ссылки с Яндекс.Диска: {e}")
            return None

class URLFileProcessor:
    """Основной класс для обработки файлов по URL"""
    
    def __init__(self, max_file_size_mb: int = 500, download_timeout: int = 1800):
        self.max_file_size_mb = max_file_size_mb
        self.download_timeout = download_timeout
        self.cloud_handler = CloudServiceHandler()
        self.session = None
        
        # Поддерживаемые MIME типы
        self.supported_mime_types = {
            # Аудио
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/wave', 'audio/x-wav',
            'audio/flac', 'audio/aac', 'audio/x-m4a', 'audio/mp4', 'audio/ogg',
            'audio/vorbis', 'audio/wma', 'audio/opus',
            # Видео
            'video/mp4', 'video/x-msvideo', 'video/avi', 'video/quicktime',
            'video/x-matroska', 'video/x-ms-wmv', 'video/webm'
        }
        
        # Поддерживаемые расширения
        self.supported_extensions = {
            '.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma', '.opus',
            '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.webm'
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.download_timeout),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def extract_urls_from_text(self, text: str) -> List[str]:
        """Извлекает все URL из текста"""
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return url_pattern.findall(text)
    
    def is_supported_url(self, url: str) -> Tuple[bool, str]:
        """
        Проверяет, поддерживается ли URL
        Returns: (is_supported, reason)
        """
        try:
            parsed = urlparse(url)
            
            if not parsed.scheme in ['http', 'https']:
                return False, "Поддерживаются только HTTP/HTTPS ссылки"
            
            if not parsed.netloc:
                return False, "Неверный формат URL"
            
            # Проверяем расширение файла в URL
            path = unquote(parsed.path)
            extension = Path(path).suffix.lower()
            
            if extension and extension not in self.supported_extensions:
                return False, f"Неподдерживаемый формат файла: {extension}"
            
            return True, "OK"
            
        except Exception as e:
            return False, f"Ошибка парсинга URL: {str(e)}"
    
    async def get_file_info(self, url: str) -> Optional[Dict]:
        """
        Получает информацию о файле по URL без скачивания
        """
        original_url = url
        try:
            # Конвертируем облачные ссылки
            is_cloud, service = self.cloud_handler.is_cloud_url(url)
            converted_url = None
            
            if is_cloud:
                converted_url = await self._convert_cloud_url(url, service)
                if converted_url and converted_url != url:
                    url = converted_url
                elif service == 'yandex_disk' and not converted_url:
                    # Если не удалось получить прямую ссылку для Яндекс.Диска
                    return {
                        'url': original_url,
                        'original_url': original_url,
                        'size_bytes': 0,
                        'size_mb': 0.0,
                        'content_type': 'text/html',
                        'filename': 'Неизвестно',
                        'is_cloud': is_cloud,
                        'cloud_service': service,
                        'supported': False,
                        'reason': 'Не удалось получить прямую ссылку для скачивания с Яндекс.Диска'
                    }
            
            # Пробуем HEAD запрос сначала
            try:
                async with self.session.head(url, allow_redirects=True) as response:
                    if response.status == 200:
                        headers = response.headers
                        response_url = str(response.url)
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
            except (aiohttp.ClientResponseError, aiohttp.ClientError):
                # Если HEAD не работает, пробуем GET с ограничением размера
                try:
                    async with self.session.get(url, allow_redirects=True) as response:
                        if response.status != 200:
                            return {
                                'url': original_url,
                                'original_url': original_url,
                                'size_bytes': 0,
                                'size_mb': 0.0,
                                'content_type': 'text/html',
                                'filename': 'Неизвестно',
                                'is_cloud': is_cloud,
                                'cloud_service': service if is_cloud else None,
                                'supported': False,
                                'reason': f'HTTP ошибка: {response.status}'
                            }
                        headers = response.headers
                        response_url = str(response.url)
                except Exception as e:
                    return {
                        'url': original_url,
                        'original_url': original_url,
                        'size_bytes': 0,
                        'size_mb': 0.0,
                        'content_type': 'text/html',
                        'filename': 'Неизвестно',
                        'is_cloud': is_cloud,
                        'cloud_service': service if is_cloud else None,
                        'supported': False,
                        'reason': f'Ошибка доступа к файлу: {str(e)}'
                    }
            
            # Получаем информацию о файле
            content_length = headers.get('content-length', '0')
            try:
                size_bytes = int(content_length)
            except (ValueError, TypeError):
                size_bytes = 0
            
            content_type = headers.get('content-type', '').split(';')[0].strip()
            
            file_info = {
                'url': response_url,
                'original_url': original_url,
                'size_bytes': size_bytes,
                'size_mb': round(size_bytes / 1024 / 1024, 2) if size_bytes > 0 else 0.0,
                'content_type': content_type,
                'filename': self._extract_filename_from_headers_and_url(headers, response_url),
                'is_cloud': is_cloud,
                'cloud_service': service if is_cloud else None,
                'supported': False,
                'reason': ''
            }
            
            # Проверяем размер файла
            if file_info['size_mb'] > self.max_file_size_mb and file_info['size_mb'] > 0:
                file_info['reason'] = f"Файл слишком большой: {file_info['size_mb']} МБ (макс. {self.max_file_size_mb} МБ)"
                return file_info
            
            # Проверяем MIME тип
            if content_type not in self.supported_mime_types:
                # Проверяем по расширению файла
                extension = Path(file_info['filename']).suffix.lower()
                if extension not in self.supported_extensions:
                    file_info['reason'] = f"Неподдерживаемый тип файла: {content_type}"
                    return file_info
            
            file_info['supported'] = True
            file_info['reason'] = 'OK'
            return file_info
                
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при получении информации о файле: {original_url}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения информации о файле {original_url}: {str(e)}")
            return None
    
    async def download_file(self, url: str, output_dir: str) -> Optional[Tuple[str, Dict]]:
        """
        Скачивает файл по URL
        Returns: (file_path, file_info) или None при ошибке
        """
        try:
            # Получаем информацию о файле
            file_info = await self.get_file_info(url)
            if not file_info:
                logger.error(f"Не удалось получить информацию о файле: {url}")
                return None
            
            if not file_info['supported']:
                logger.error(f"Файл не поддерживается: {file_info['reason']}")
                return None
            
            # Создаем временную директорию для скачивания
            os.makedirs(output_dir, exist_ok=True)
            
            # Определяем имя файла
            filename = file_info['filename']
            if not filename or filename in ['UTF-8', 'utf-8', 'unknown_file', 'downloaded_file']:
                # Генерируем имя файла на основе content-type и URL
                base_name = f"file_{hash(url) % 10000}"
                extension = self._get_extension_from_mime(file_info['content_type'])
                
                if not extension and file_info['is_cloud'] and file_info['cloud_service'] == 'yandex_disk':
                    # Для Яндекс.Диска по умолчанию используем расширение на основе MIME
                    if 'audio' in file_info['content_type']:
                        extension = '.mp3'
                    elif 'video' in file_info['content_type']:
                        extension = '.mp4'
                
                filename = base_name + (extension or '.bin')
            
            # Убеждаемся, что имя файла безопасно
            filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            if not filename:
                filename = f"downloaded_file_{hash(url) % 10000}.bin"
            
            file_path = os.path.join(output_dir, filename)
            
            # Скачиваем файл
            download_url = file_info['url']
            logger.info(f"Скачиваю файл: {download_url} -> {file_path}")
            
            async with self.session.get(download_url) as response:
                if response.status != 200:
                    logger.error(f"Ошибка скачивания файла: HTTP {response.status}")
                    return None
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(file_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Логируем прогресс каждые 10 МБ
                        if downloaded_size % (10 * 1024 * 1024) == 0:
                            progress = (downloaded_size / total_size * 100) if total_size > 0 else 0
                            logger.info(f"Скачано: {downloaded_size / 1024 / 1024:.1f} МБ ({progress:.1f}%)")
            
            # Проверяем размер скачанного файла
            actual_size = os.path.getsize(file_path)
            if total_size > 0 and actual_size != total_size:
                logger.warning(f"Размер файла не совпадает: ожидали {total_size}, получили {actual_size}")
            
            file_info['downloaded_size'] = actual_size
            file_info['local_path'] = file_path
            
            logger.info(f"Файл успешно скачан: {file_path} ({actual_size / 1024 / 1024:.2f} МБ)")
            return file_path, file_info
            
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при скачивании файла: {url}")
            return None
        except Exception as e:
            logger.error(f"Ошибка скачивания файла {url}: {str(e)}")
            return None
    
    async def _convert_cloud_url(self, url: str, service: str) -> Optional[str]:
        """Конвертирует облачную ссылку в прямую ссылку для скачивания"""
        try:
            if service == 'google_drive':
                return self.cloud_handler.convert_google_drive_url(url)
            elif service == 'yandex_disk':
                # Для Яндекс.Диска используем API для получения прямой ссылки
                direct_url = await self.cloud_handler.get_yandex_disk_download_url(self.session, url)
                return direct_url if direct_url else url
            else:
                return url
        except Exception as e:
            logger.error(f"Ошибка конвертации облачной ссылки {url}: {str(e)}")
            return url
    
    def _extract_filename(self, response, url: str) -> str:
        """Извлекает имя файла из response или URL"""
        return self._extract_filename_from_headers_and_url(response.headers, url)
    
    def _extract_filename_from_headers_and_url(self, headers, url: str) -> str:
        """Извлекает имя файла из заголовков и URL"""
        # Проверяем заголовок Content-Disposition
        content_disposition = headers.get('content-disposition', '')
        if content_disposition:
            # Более точный парсинг Content-Disposition
            patterns = [
                r'filename\*=UTF-8\'\'([^;\r\n]+)',  # RFC 5987 encoded filename
                r'filename="([^"]+)"',                # Quoted filename
                r'filename=([^;\s]+)',                # Unquoted filename
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content_disposition, re.IGNORECASE)
                if match:
                    filename = unquote(match.group(1))
                    # Проверяем, что это не служебная информация
                    if filename and len(filename) > 1 and filename not in ['UTF-8', 'utf-8', 'unknown']:
                        # Если файл без расширения, пробуем определить по content-type
                        if '.' not in filename:
                            continue
                        # Очищаем имя файла от проблемных символов
                        filename = self._clean_filename(filename)
                        return filename
        
        # Извлекаем из URL
        parsed = urlparse(url)
        path = unquote(parsed.path)
        filename = Path(path).name
        
        if filename and '.' in filename and len(filename) > 1:
            filename = self._clean_filename(filename)
            return filename
        
        # Если ничего не найдено, генерируем имя на основе URL
        if 'yandex' in url.lower():
            return "yandex_disk_file.mp3"  # По умолчанию для Яндекс.Диска
        
        return "downloaded_file"
    
    def _clean_filename(self, filename: str) -> str:
        """Очищает имя файла от проблемных символов"""
        if not filename:
            return "unknown_file"
        
        # Заменяем обратные слеши на обычные слеши или подчеркивания
        filename = filename.replace('\\', '_')
        
        # Заменяем другие проблемные символы
        problematic_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in problematic_chars:
            filename = filename.replace(char, '_')
        
        # Убираем множественные подчеркивания
        while '__' in filename:
            filename = filename.replace('__', '_')
        
        # Убираем подчеркивания в начале и конце
        filename = filename.strip('_')
        
        return filename if filename else "cleaned_file"
    
    def _get_extension_from_mime(self, mime_type: str) -> str:
        """Получает расширение файла по MIME типу"""
        mime_to_ext = {
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/wav': '.wav',
            'audio/wave': '.wav',
            'audio/x-wav': '.wav',
            'audio/flac': '.flac',
            'audio/aac': '.aac',
            'audio/x-m4a': '.m4a',
            'audio/mp4': '.m4a',
            'audio/ogg': '.ogg',
            'audio/vorbis': '.ogg',
            'video/mp4': '.mp4',
            'video/x-msvideo': '.avi',
            'video/avi': '.avi',
            'video/quicktime': '.mov',
            'video/x-matroska': '.mkv',
            'video/x-ms-wmv': '.wmv',
            'video/webm': '.webm'
        }
        
        return mime_to_ext.get(mime_type, '')

class URLValidator:
    """Валидатор URL с дополнительными проверками безопасности"""
    
    def __init__(self, allowed_domains: List[str] = None, blocked_domains: List[str] = None):
        self.allowed_domains = allowed_domains or []
        self.blocked_domains = blocked_domains or []
    
    def is_safe_url(self, url: str) -> Tuple[bool, str]:
        """
        Проверяет безопасность URL
        Returns: (is_safe, reason)
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Проверяем заблокированные домены
            if self.blocked_domains:
                for blocked in self.blocked_domains:
                    if blocked in domain:
                        return False, f"Домен заблокирован: {domain}"
            
            # Проверяем разрешенные домены (если указаны)
            if self.allowed_domains:
                allowed = False
                for allowed_domain in self.allowed_domains:
                    if allowed_domain in domain:
                        allowed = True
                        break
                
                if not allowed:
                    return False, f"Домен не разрешен: {domain}"
            
            # Проверяем на локальные адреса
            if domain in ['localhost', '127.0.0.1', '0.0.0.0'] or domain.startswith('192.168.') or domain.startswith('10.'):
                return False, "Локальные адреса не разрешены"
            
            return True, "OK"
            
        except Exception as e:
            return False, f"Ошибка валидации URL: {str(e)}"