#!/usr/bin/env python3
"""
Confluence Server API Client для интеграции с системой обработки встреч
Поддерживает только Confluence Server с Personal Access Token аутентификацией
"""

import requests
import json
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
import time
from cryptography.fernet import Fernet
import base64
import hashlib

from database.models import ConfluencePublication, PublicationStatus
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ConfluenceError(Exception):
    """Базовый класс для ошибок Confluence API"""
    pass


class ConfluenceAuthenticationError(ConfluenceError):
    """Ошибка аутентификации в Confluence"""
    pass


class ConfluencePermissionError(ConfluenceError):
    """Ошибка прав доступа в Confluence"""
    pass


class ConfluenceNotFoundError(ConfluenceError):
    """Ошибка - ресурс не найден в Confluence"""
    pass


class ConfluenceValidationError(ConfluenceError):
    """Ошибка валидации данных для Confluence"""
    pass


class ConfluenceNetworkError(ConfluenceError):
    """Ошибка сети при обращении к Confluence"""
    pass


@dataclass
class ConfluenceConfig:
    """Конфигурация для подключения к Confluence Server"""
    base_url: str
    api_token: str
    space_key: str
    username: Optional[str] = None  # Опциональное поле для совместимости
    parent_page_id: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


class ConfluenceEncryption:
    """Утилиты для шифрования токенов Confluence"""
    
    @staticmethod
    def generate_key() -> str:
        """Генерирует ключ шифрования"""
        return Fernet.generate_key().decode()
    
    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[str] = None) -> str:
        """Создает ключ шифрования из пароля"""
        if salt is None:
            salt = "confluence_meeting_processor_salt"
        
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return base64.urlsafe_b64encode(key).decode()
    
    @staticmethod
    def encrypt_token(token: str, key: str) -> str:
        """Шифрует токен"""
        try:
            fernet = Fernet(key.encode())
            encrypted_token = fernet.encrypt(token.encode())
            return base64.urlsafe_b64encode(encrypted_token).decode()
        except Exception as e:
            raise ConfluenceError(f"Ошибка шифрования токена: {e}")
    
    @staticmethod
    def decrypt_token(encrypted_token: str, key: str) -> str:
        """Расшифровывает токен"""
        try:
            fernet = Fernet(key.encode())
            encrypted_data = base64.urlsafe_b64decode(encrypted_token.encode())
            decrypted_token = fernet.decrypt(encrypted_data)
            return decrypted_token.decode()
        except Exception as e:
            raise ConfluenceError(f"Ошибка расшифровки токена: {e}")


class ConfluenceContentProcessor:
    """Процессор для конвертации Markdown в Confluence Storage Format"""
    
    @staticmethod
    def markdown_to_confluence(markdown_content: str) -> str:
        """
        Конвертирует Markdown в Confluence Storage Format
        
        Args:
            markdown_content: Содержимое в формате Markdown
            
        Returns:
            Содержимое в формате Confluence Storage Format
        """
        # Базовая конвертация Markdown в Confluence Storage Format
        content = markdown_content
        
        # Заголовки
        content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', content, flags=re.MULTILINE)
        content = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', content, flags=re.MULTILINE)
        content = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', content, flags=re.MULTILINE)
        
        # Жирный текст
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'__(.+?)__', r'<strong>\1</strong>', content)
        
        # Блоки кода (обрабатываем ПЕРЕД inline кодом)
        def replace_code_block(match):
            language = match.group(1) if match.group(1) else ''
            code_content = match.group(2)
            if language:
                return f'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">{language}</ac:parameter><ac:plain-text-body><![CDATA[{code_content}]]></ac:plain-text-body></ac:structured-macro>'
            else:
                return f'<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA[{code_content}]]></ac:plain-text-body></ac:structured-macro>'
        
        content = re.sub(
            r'```(\w+)?\n(.*?)\n```',
            replace_code_block,
            content,
            flags=re.DOTALL
        )
        
        # Курсив
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        content = re.sub(r'_(.+?)_', r'<em>\1</em>', content)
        
        # Код (inline)
        content = re.sub(r'`(.+?)`', r'<code>\1</code>', content)
        
        # Таблицы (обрабатываем ПЕРЕД списками)
        content = ConfluenceContentProcessor._convert_tables(content)
        
        # Списки (неупорядоченные)
        lines = content.split('\n')
        in_list = False
        processed_lines = []
        
        for line in lines:
            if re.match(r'^[\s]*[-*+]\s+(.+)', line):
                if not in_list:
                    processed_lines.append('<ul>')
                    in_list = True
                indent_level = len(line) - len(line.lstrip())
                item_text = re.sub(r'^[\s]*[-*+]\s+(.+)', r'\1', line)
                processed_lines.append(f'<li>{item_text}</li>')
            else:
                if in_list:
                    processed_lines.append('</ul>')
                    in_list = False
                processed_lines.append(line)
        
        if in_list:
            processed_lines.append('</ul>')
        
        content = '\n'.join(processed_lines)
        
        # Упорядоченные списки
        content = re.sub(r'^\d+\.\s+(.+)$', r'<ol><li>\1</li></ol>', content, flags=re.MULTILINE)
        
        # Ссылки
        content = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', content)
        
        # Разрывы строк
        content = re.sub(r'\n\n+', '</p><p>', content)
        content = f'<p>{content}</p>'
        
        # Очистка пустых параграфов
        content = re.sub(r'<p></p>', '', content)
        content = re.sub(r'<p>\s*</p>', '', content)
        
        return content
    
    @staticmethod
    def _convert_tables(content: str) -> str:
        """
        Конвертирует Markdown таблицы в Confluence Storage Format
        
        Args:
            content: Содержимое с Markdown таблицами
            
        Returns:
            Содержимое с Confluence таблицами
        """
        lines = content.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Проверяем, является ли строка заголовком таблицы (содержит |)
            if '|' in line and line.startswith('|') and line.endswith('|'):
                # Ищем следующую строку с разделителями (---|---|---)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'^\|[\s\-\|:]+\|$', next_line):
                        # Это таблица! Обрабатываем её
                        table_lines = [line]
                        separator_line = next_line
                        i += 2  # Пропускаем строку разделителя
                        
                        # Собираем все строки таблицы
                        while i < len(lines):
                            table_line = lines[i].strip()
                            if '|' in table_line and table_line.startswith('|') and table_line.endswith('|'):
                                table_lines.append(table_line)
                                i += 1
                            else:
                                break
                        
                        # Конвертируем таблицу в Confluence формат
                        confluence_table = ConfluenceContentProcessor._markdown_table_to_confluence(table_lines)
                        result_lines.append(confluence_table)
                        continue
            
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines)
    
    @staticmethod
    def _markdown_table_to_confluence(table_lines: List[str]) -> str:
        """
        Конвертирует Markdown таблицу в Confluence Storage Format
        
        Args:
            table_lines: Строки таблицы в Markdown формате
            
        Returns:
            Таблица в Confluence Storage Format
        """
        if not table_lines:
            return ""
        
        # Парсим заголовок
        header_line = table_lines[0]
        header_cells = [cell.strip() for cell in header_line.split('|')[1:-1]]  # Убираем пустые элементы по краям
        
        # Парсим строки данных
        data_rows = []
        for line in table_lines[1:]:  # Пропускаем заголовок
            cells = [cell.strip() for cell in line.split('|')[1:-1]]  # Убираем пустые элементы по краям
            if cells:  # Проверяем, что строка не пустая
                data_rows.append(cells)
        
        # Строим Confluence таблицу
        confluence_table = '<table><tbody>'
        
        # Добавляем заголовок
        if header_cells:
            confluence_table += '<tr>'
            for cell in header_cells:
                confluence_table += f'<th><p>{cell}</p></th>'
            confluence_table += '</tr>'
        
        # Добавляем строки данных
        for row in data_rows:
            confluence_table += '<tr>'
            for cell in row:
                confluence_table += f'<td><p>{cell}</p></td>'
            confluence_table += '</tr>'
        
        confluence_table += '</tbody></table>'
        
        return confluence_table
    
    @staticmethod
    def extract_meeting_info(content: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Извлекает дату и тему встречи из содержимого протокола
        
        Args:
            content: Содержимое протокола
            
        Returns:
            Кортеж (дата, тема встречи)
        """
        date_pattern = r'(?:дата|date):\s*(\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{4}-\d{2}-\d{2})'
        topic_pattern = r'(?:тема|topic|subject):\s*\*?\*?\s*(.+?)(?:\n|$)'
        
        date_match = re.search(date_pattern, content, re.IGNORECASE)
        topic_match = re.search(topic_pattern, content, re.IGNORECASE)
        
        meeting_date = date_match.group(1) if date_match else None
        meeting_topic = topic_match.group(1).strip() if topic_match else None
        
        # Попытка извлечь дату из заголовка
        if not meeting_date:
            header_date_pattern = r'(\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{2,4})'
            header_match = re.search(header_date_pattern, content[:200])
            if header_match:
                meeting_date = header_match.group(1)
        
        # Попытка извлечь тему из первого заголовка
        if not meeting_topic:
            header_pattern = r'^#\s*(.+?)$'
            header_match = re.search(header_pattern, content, re.MULTILINE)
            if header_match:
                meeting_topic = header_match.group(1).strip()
        
        return meeting_date, meeting_topic
    
    @staticmethod
    def generate_page_title(meeting_date: Optional[str], meeting_topic: Optional[str], 
                          fallback_filename: Optional[str] = None) -> str:
        """
        Генерирует заголовок страницы в формате YYYY-MM-DD <тема встречи>
        
        Args:
            meeting_date: Дата встречи
            meeting_topic: Тема встречи
            fallback_filename: Резервное имя файла
            
        Returns:
            Заголовок страницы
        """
        # Нормализация даты
        formatted_date = None
        if meeting_date:
            # Попытка парсинга различных форматов даты
            date_formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%d.%m.%y', '%d/%m/%y']
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(meeting_date, fmt)
                    formatted_date = parsed_date.strftime('%Y-%m-%d')  # Формат YYYYMMDD без дефисов
                    break
                except ValueError:
                    continue
        
        if not formatted_date:
            formatted_date = datetime.now().strftime('%Y-%m-%d')  # Формат YYYYMMDD без дефисов
        
        # Очистка темы встречи
        if meeting_topic:
            # Удаляем лишние символы и ограничиваем длину
            clean_topic = re.sub(r'[^\w\s\-.,()]+', '', meeting_topic)
            clean_topic = clean_topic.strip()[:100]
        else:
            clean_topic = fallback_filename or "Протокол встречи"
        
        return f"{formatted_date} {clean_topic}"  # Добавляем дефис между датой и темой


class ConfluenceServerClient:
    """Клиент для работы с Confluence Server REST API"""
    
    def __init__(self, config: ConfluenceConfig):
        """
        Инициализация клиента Confluence Server
        
        Args:
            config: Конфигурация подключения к Confluence Server
        """
        self.config = config
        self.session = requests.Session()
        
        # Используем Personal Access Token для аутентификации в Confluence Server
        self.session.headers.update({
            'Authorization': f'Bearer {config.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        logger.info("Используется Personal Access Token для Confluence Server")
        
        # Валидация конфигурации
        self._validate_config()
        
        logger.info(f"Инициализирован Confluence Server клиент для {config.base_url}")
    
    def _validate_config(self):
        """Валидирует конфигурацию"""
        if not self.config.base_url:
            raise ConfluenceValidationError("Не указан base_url")
        
        if not self.config.api_token:
            raise ConfluenceValidationError("Не указан Personal Access Token")
        
        if not self.config.space_key:
            raise ConfluenceValidationError("Не указан space_key")
        
        # Проверка формата URL
        try:
            parsed_url = urlparse(self.config.base_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ConfluenceValidationError("Некорректный формат base_url")
        except Exception:
            raise ConfluenceValidationError("Некорректный формат base_url")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Выполняет HTTP запрос с обработкой ошибок и повторными попытками
        
        Args:
            method: HTTP метод
            endpoint: Конечная точка API
            **kwargs: Дополнительные параметры для requests
            
        Returns:
            Ответ сервера
        """
        url = urljoin(self.config.base_url.rstrip('/') + '/', endpoint.lstrip('/'))
        
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.config.timeout,
                    **kwargs
                )
                
                # Обработка HTTP ошибок
                if response.status_code == 401:
                    raise ConfluenceAuthenticationError("Ошибка аутентификации")
                elif response.status_code == 403:
                    raise ConfluencePermissionError("Недостаточно прав доступа")
                elif response.status_code == 404:
                    raise ConfluenceNotFoundError("Ресурс не найден")
                elif response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    raise ConfluenceError(error_msg)
                
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise ConfluenceNetworkError(f"Ошибка сети: {e}")
                
                logger.warning(f"Попытка {attempt + 1} неудачна, повтор через {self.config.retry_delay}с")
                time.sleep(self.config.retry_delay)
        
        raise ConfluenceNetworkError("Превышено максимальное количество попыток")
    
    def test_connection(self) -> bool:
        """
        Тестирует подключение к Confluence
        
        Returns:
            True если подключение успешно
        """
        try:
            response = self._make_request('GET', '/rest/api/space')
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ошибка тестирования подключения: {e}")
            return False
    
    def get_space_info(self, space_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает информацию о пространстве
        
        Args:
            space_key: Ключ пространства (по умолчанию из конфигурации)
            
        Returns:
            Информация о пространстве
        """
        space_key = space_key or self.config.space_key
        response = self._make_request('GET', f'/rest/api/space/{space_key}')
        return response.json()
    
    def get_page_info(self, page_id: str) -> Dict[str, Any]:
        """
        Получает информацию о странице
        
        Args:
            page_id: ID страницы
            
        Returns:
            Информация о странице
        """
        response = self._make_request(
            'GET', 
            f'/rest/api/content/{page_id}',
            params={'expand': 'space,version,ancestors'}
        )
        return response.json()
    
    def create_page(self, title: str, content: str, parent_page_id: Optional[str] = None,
                   space_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Создает новую страницу в Confluence
        
        Args:
            title: Заголовок страницы
            content: Содержимое страницы в Storage Format
            parent_page_id: ID родительской страницы
            space_key: Ключ пространства
            
        Returns:
            Информация о созданной странице
        """
        space_key = space_key or self.config.space_key
        parent_page_id = parent_page_id or self.config.parent_page_id
        
        page_data = {
            'type': 'page',
            'title': title,
            'space': {'key': space_key},
            'body': {
                'storage': {
                    'value': content,
                    'representation': 'storage'
                }
            }
        }
        
        if parent_page_id:
            page_data['ancestors'] = [{'id': parent_page_id}]
        
        response = self._make_request(
            'POST',
            '/rest/api/content',
            json=page_data
        )
        
        return response.json()
    
    def update_page(self, page_id: str, title: str, content: str, 
                   version_number: int) -> Dict[str, Any]:
        """
        Обновляет существующую страницу
        
        Args:
            page_id: ID страницы
            title: Новый заголовок
            content: Новое содержимое
            version_number: Номер версии
            
        Returns:
            Информация об обновленной странице
        """
        page_data = {
            'version': {'number': version_number + 1},
            'title': title,
            'type': 'page',
            'body': {
                'storage': {
                    'value': content,
                    'representation': 'storage'
                }
            }
        }
        
        response = self._make_request(
            'PUT',
            f'/rest/api/content/{page_id}',
            json=page_data
        )
        
        return response.json()
    
    def delete_page(self, page_id: str) -> bool:
        """
        Удаляет страницу
        
        Args:
            page_id: ID страницы
            
        Returns:
            True если удаление успешно
        """
        try:
            self._make_request('DELETE', f'/rest/api/content/{page_id}')
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления страницы {page_id}: {e}")
            return False
    
    def search_pages(self, query: str, space_key: Optional[str] = None, 
                    limit: int = 25) -> List[Dict[str, Any]]:
        """
        Поиск страниц в Confluence
        
        Args:
            query: Поисковый запрос
            space_key: Ключ пространства
            limit: Лимит результатов
            
        Returns:
            Список найденных страниц
        """
        space_key = space_key or self.config.space_key
        
        params = {
            'cql': f'space = "{space_key}" AND text ~ "{query}"',
            'limit': limit
        }
        
        response = self._make_request('GET', '/rest/api/content/search', params=params)
        return response.json().get('results', [])


class ConfluencePublicationService:
    """Сервис для публикации протоколов встреч в Confluence"""
    
    def __init__(self, confluence_client: ConfluenceServerClient, 
                 db_manager: DatabaseManager):
        """
        Инициализация сервиса
        
        Args:
            confluence_client: Клиент Confluence API
            db_manager: Менеджер базы данных
        """
        self.confluence_client = confluence_client
        self.db_manager = db_manager
        self.content_processor = ConfluenceContentProcessor()
        
        logger.info("Инициализирован сервис публикации в Confluence")
    
    def publish_meeting_protocol(self, job_id: str, protocol_content: str,
                               filename: Optional[str] = None, parent_page_id: Optional[str] = None) -> ConfluencePublication:
        """
        Публикует протокол встречи в Confluence
        
        Args:
            job_id: ID задачи
            protocol_content: Содержимое протокола в Markdown
            filename: Имя файла (для fallback заголовка)
            parent_page_id: ID родительской страницы (переопределяет конфигурацию)
            
        Returns:
            Объект публикации в Confluence
        """
        try:
            # Извлекаем информацию о встрече
            meeting_date, meeting_topic = self.content_processor.extract_meeting_info(
                protocol_content
            )
            
            # Генерируем заголовок страницы
            page_title = self.content_processor.generate_page_title(
                meeting_date, meeting_topic, filename
            )
            
            # Конвертируем содержимое в Confluence Storage Format
            confluence_content = self.content_processor.markdown_to_confluence(
                protocol_content
            )
            
            # Создаем страницу в Confluence
            page_info = self.confluence_client.create_page(
                title=page_title,
                content=confluence_content,
                parent_page_id=parent_page_id
            )
            
            # Создаем запись о публикации в БД
            publication_data = {
                'job_id': job_id,
                'confluence_page_id': page_info['id'],
                'confluence_page_url': self._build_page_url(page_info),
                'confluence_space_key': self.confluence_client.config.space_key,
                'parent_page_id': self.confluence_client.config.parent_page_id,
                'page_title': page_title,
                'publication_status': PublicationStatus.PUBLISHED
            }
            
            publication = ConfluencePublication.from_dict(publication_data)
            
            # Сохраняем в БД
            self._save_publication_to_db(publication)
            
            logger.info(f"Протокол успешно опубликован: {page_info['_links']['webui']}")
            
            return publication
            
        except Exception as e:
            logger.error(f"Ошибка публикации протокола для задачи {job_id}: {e}")
            
            # Создаем запись об ошибке
            error_publication = ConfluencePublication(
                job_id=job_id,
                confluence_page_id="",
                confluence_page_url="",
                confluence_space_key=self.confluence_client.config.space_key,
                page_title=f"Ошибка публикации - {datetime.now().strftime('%Y%m%d')}",
                publication_status=PublicationStatus.FAILED,
                error_message=str(e)
            )
            
            self._save_publication_to_db(error_publication)
            raise ConfluenceError(f"Ошибка публикации: {e}")
    
    def retry_failed_publication(self, publication_id: int) -> ConfluencePublication:
        """
        Повторная попытка публикации
        
        Args:
            publication_id: ID публикации
            
        Returns:
            Обновленный объект публикации
        """
        # Получаем публикацию из БД
        publication = self._get_publication_from_db(publication_id)
        
        if not publication:
            raise ConfluenceNotFoundError(f"Публикация {publication_id} не найдена")
        
        if publication.publication_status != PublicationStatus.FAILED:
            raise ConfluenceValidationError("Можно повторить только неудачные публикации")
        
        # Получаем исходную задачу
        job = self.db_manager.get_job_by_id(publication.job_id)
        if not job:
            raise ConfluenceNotFoundError(f"Задача {publication.job_id} не найдена")
        
        try:
            # Обновляем статус на "повтор"
            publication.publication_status = PublicationStatus.RETRYING
            publication.increment_retry_count()
            self._update_publication_in_db(publication)
            
            # Читаем содержимое протокола
            if not job.get('summary_file'):
                raise ConfluenceValidationError("Файл протокола не найден")
            
            with open(job['summary_file'], 'r', encoding='utf-8') as f:
                protocol_content = f.read()
            
            # Повторная публикация
            return self.publish_meeting_protocol(
                job_id=publication.job_id,
                protocol_content=protocol_content,
                filename=job.get('filename')
            )
            
        except Exception as e:
            # Обновляем ошибку
            publication.publication_status = PublicationStatus.FAILED
            publication.error_message = str(e)
            self._update_publication_in_db(publication)
            raise
    
    def get_job_publications(self, job_id: str) -> List[ConfluencePublication]:
        """
        Получает все публикации для задачи
        
        Args:
            job_id: ID задачи
            
        Returns:
            Список публикаций
        """
        return self._get_publications_by_job_id(job_id)
    
    def delete_publication(self, publication_id: int, delete_from_confluence: bool = True) -> bool:
        """
        Удаляет публикацию
        
        Args:
            publication_id: ID публикации
            delete_from_confluence: Удалять ли страницу из Confluence
            
        Returns:
            True если удаление успешно
        """
        publication = self._get_publication_from_db(publication_id)
        
        if not publication:
            return False
        
        try:
            # Удаляем из Confluence если требуется
            if delete_from_confluence and publication.confluence_page_id:
                self.confluence_client.delete_page(publication.confluence_page_id)
            
            # Удаляем из БД
            return self._delete_publication_from_db(publication_id)
            
        except Exception as e:
            logger.error(f"Ошибка удаления публикации {publication_id}: {e}")
            return False
    
    def _build_page_url(self, page_info: Dict[str, Any]) -> str:
        """Строит URL страницы"""
        base_url = self.confluence_client.config.base_url.rstrip('/')
        web_ui_link = page_info.get('_links', {}).get('webui', '')
        return f"{base_url}{web_ui_link}"
    
    def _save_publication_to_db(self, publication: ConfluencePublication):
        """Сохраняет публикацию в БД"""
        publication_data = publication.to_dict()
        # Убираем id для создания новой записи
        publication_data.pop('id', None)
        
        created_publication = self.db_manager.create_confluence_publication(publication_data)
        publication.id = created_publication['id']
    
    def _update_publication_in_db(self, publication: ConfluencePublication):
        """Обновляет публикацию в БД"""
        if publication.id:
            publication_data = publication.to_dict()
            self.db_manager.update_confluence_publication(publication.id, publication_data)
    
    def _get_publication_from_db(self, publication_id: int) -> Optional[ConfluencePublication]:
        """Получает публикацию из БД"""
        publication_data = self.db_manager.get_confluence_publication_by_id(publication_id)
        if publication_data:
            return ConfluencePublication.from_dict(publication_data)
        return None
    
    def _get_publications_by_job_id(self, job_id: str) -> List[ConfluencePublication]:
        """Получает публикации по ID задачи"""
        publications_data = self.db_manager.get_confluence_publications_by_job_id(job_id)
        return [ConfluencePublication.from_dict(data) for data in publications_data]
    
    def _delete_publication_from_db(self, publication_id: int) -> bool:
        """Удаляет публикацию из БД"""
        return self.db_manager.delete_confluence_publication(publication_id)


def create_confluence_client(config: Dict[str, Any]) -> ConfluenceServerClient:
    """
    Создает клиент Confluence из конфигурации
    
    Args:
        config: Конфигурация приложения
        
    Returns:
        Настроенный клиент Confluence
    """
    confluence_config = config.get('confluence', {})
    
    if not confluence_config.get('enabled', False):
        raise ConfluenceValidationError("Confluence интеграция отключена")
    
    # Расшифровка токена если необходимо
    api_token = confluence_config.get('api_token')
    encryption_key = confluence_config.get('encryption_key')
    
    if encryption_key and api_token:
        try:
            api_token = ConfluenceEncryption.decrypt_token(api_token, encryption_key)
        except Exception as e:
            logger.warning(f"Не удалось расшифровать токен: {e}")
    
    client_config = ConfluenceConfig(
        base_url=confluence_config['base_url'],
        api_token=api_token,
        space_key=confluence_config['space_key'],
        username=confluence_config.get('username'),  # Опциональное поле для совместимости
        parent_page_id=confluence_config.get('parent_page_id'),
        timeout=confluence_config.get('timeout', 30),
        max_retries=confluence_config.get('max_retries', 3),
        retry_delay=confluence_config.get('retry_delay', 1.0)
    )
    
    return ConfluenceServerClient(client_config)


def create_confluence_publication_service(config: Dict[str, Any], 
                                         db_manager: DatabaseManager) -> ConfluencePublicationService:
    """
    Создает сервис публикации в Confluence
    
    Args:
        config: Конфигурация приложения
        db_manager: Менеджер базы данных
        
    Returns:
        Настроенный сервис публикации
    """
    confluence_client = create_


def create_confluence_publication_service(config: Dict[str, Any], 
                                         db_manager: DatabaseManager) -> ConfluencePublicationService:
    """
    Создает сервис публикации в Confluence
    
    Args:
        config: Конфигурация приложения
        db_manager: Менеджер базы данных
        
    Returns:
        Настроенный сервис публикации
    """
    confluence_client = create_confluence_client(config)
    return ConfluencePublicationService(confluence_client, db_manager)