#!/usr/bin/env python3
"""
Утилиты шифрования для безопасного хранения токенов Confluence
"""

import os
import base64
import hashlib
import secrets
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Базовый класс для ошибок шифрования"""
    pass


class EncryptionKeyError(EncryptionError):
    """Ошибка работы с ключами шифрования"""
    pass


class EncryptionDataError(EncryptionError):
    """Ошибка шифрования/расшифровки данных"""
    pass


class ConfluenceTokenManager:
    """Менеджер для безопасного хранения и управления токенами Confluence"""
    
    def __init__(self, config_path: str = "confluence_tokens.json"):
        """
        Инициализация менеджера токенов
        
        Args:
            config_path: Путь к файлу с зашифрованными токенами
        """
        self.config_path = Path(config_path)
        self.salt_length = 32
        self.iterations = 100000
        
        logger.info(f"Инициализирован менеджер токенов: {self.config_path}")
    
    def generate_master_key(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Генерирует мастер-ключ из пароля
        
        Args:
            password: Пароль для генерации ключа
            salt: Соль (если не указана, генерируется новая)
            
        Returns:
            Кортеж (ключ, соль)
        """
        if salt is None:
            salt = secrets.token_bytes(self.salt_length)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def encrypt_token(self, token: str, password: str) -> Dict[str, str]:
        """
        Шифрует токен с использованием пароля
        
        Args:
            token: Токен для шифрования
            password: Пароль для шифрования
            
        Returns:
            Словарь с зашифрованными данными
        """
        try:
            # Генерируем ключ и соль
            key, salt = self.generate_master_key(password)
            
            # Создаем Fernet объект
            fernet = Fernet(key)
            
            # Шифруем токен
            encrypted_token = fernet.encrypt(token.encode())
            
            # Возвращаем данные в base64
            return {
                'encrypted_token': base64.urlsafe_b64encode(encrypted_token).decode(),
                'salt': base64.urlsafe_b64encode(salt).decode(),
                'algorithm': 'PBKDF2-SHA256',
                'iterations': self.iterations
            }
            
        except Exception as e:
            raise EncryptionDataError(f"Ошибка шифрования токена: {e}")
    
    def decrypt_token(self, encrypted_data: Dict[str, str], password: str) -> str:
        """
        Расшифровывает токен
        
        Args:
            encrypted_data: Зашифрованные данные
            password: Пароль для расшифровки
            
        Returns:
            Расшифрованный токен
        """
        try:
            # Извлекаем данные
            encrypted_token = base64.urlsafe_b64decode(encrypted_data['encrypted_token'])
            salt = base64.urlsafe_b64decode(encrypted_data['salt'])
            
            # Генерируем ключ
            key, _ = self.generate_master_key(password, salt)
            
            # Создаем Fernet объект
            fernet = Fernet(key)
            
            # Расшифровываем токен
            decrypted_token = fernet.decrypt(encrypted_token)
            
            return decrypted_token.decode()
            
        except Exception as e:
            raise EncryptionDataError(f"Ошибка расшифровки токена: {e}")
    
    def save_encrypted_token(self, token: str, password: str, 
                           confluence_url: str, username: str) -> bool:
        """
        Сохраняет зашифрованный токен в файл
        
        Args:
            token: Токен для сохранения
            password: Пароль для шифрования
            confluence_url: URL Confluence
            username: Имя пользователя
            
        Returns:
            True если сохранение успешно
        """
        try:
            # Шифруем токен
            encrypted_data = self.encrypt_token(token, password)
            
            # Создаем структуру данных
            token_data = {
                'confluence_url': confluence_url,
                'username': username,
                'encrypted_token_data': encrypted_data,
                'created_at': self._get_current_timestamp(),
                'last_used': None
            }
            
            # Загружаем существующие данные
            existing_data = self._load_token_file()
            
            # Создаем ключ для токена
            token_key = self._generate_token_key(confluence_url, username)
            
            # Сохраняем токен
            existing_data[token_key] = token_data
            
            # Записываем в файл
            self._save_token_file(existing_data)
            
            logger.info(f"Токен сохранен для {username}@{confluence_url}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения токена: {e}")
            return False
    
    def load_encrypted_token(self, password: str, confluence_url: str, 
                           username: str) -> Optional[str]:
        """
        Загружает и расшифровывает токен
        
        Args:
            password: Пароль для расшифровки
            confluence_url: URL Confluence
            username: Имя пользователя
            
        Returns:
            Расшифрованный токен или None
        """
        try:
            # Загружаем данные
            token_data = self._load_token_file()
            
            # Создаем ключ для токена
            token_key = self._generate_token_key(confluence_url, username)
            
            if token_key not in token_data:
                logger.warning(f"Токен не найден для {username}@{confluence_url}")
                return None
            
            # Получаем зашифрованные данные
            encrypted_data = token_data[token_key]['encrypted_token_data']
            
            # Расшифровываем токен
            decrypted_token = self.decrypt_token(encrypted_data, password)
            
            # Обновляем время последнего использования
            token_data[token_key]['last_used'] = self._get_current_timestamp()
            self._save_token_file(token_data)
            
            logger.info(f"Токен успешно загружен для {username}@{confluence_url}")
            return decrypted_token
            
        except Exception as e:
            logger.error(f"Ошибка загрузки токена: {e}")
            return None
    
    def delete_token(self, confluence_url: str, username: str) -> bool:
        """
        Удаляет сохраненный токен
        
        Args:
            confluence_url: URL Confluence
            username: Имя пользователя
            
        Returns:
            True если удаление успешно
        """
        try:
            # Загружаем данные
            token_data = self._load_token_file()
            
            # Создаем ключ для токена
            token_key = self._generate_token_key(confluence_url, username)
            
            if token_key in token_data:
                del token_data[token_key]
                self._save_token_file(token_data)
                logger.info(f"Токен удален для {username}@{confluence_url}")
                return True
            else:
                logger.warning(f"Токен не найден для удаления: {username}@{confluence_url}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка удаления токена: {e}")
            return False
    
    def list_saved_tokens(self) -> List[Dict[str, str]]:
        """
        Возвращает список сохраненных токенов (без самих токенов)
        
        Returns:
            Список информации о токенах
        """
        try:
            token_data = self._load_token_file()
            
            result = []
            for token_key, data in token_data.items():
                result.append({
                    'confluence_url': data['confluence_url'],
                    'username': data['username'],
                    'created_at': data['created_at'],
                    'last_used': data.get('last_used', 'Никогда')
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения списка токенов: {e}")
            return []
    
    def validate_token_file_integrity(self) -> bool:
        """
        Проверяет целостность файла с токенами
        
        Returns:
            True если файл корректен
        """
        try:
            if not self.config_path.exists():
                return True  # Файл не существует - это нормально
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем структуру данных
            if not isinstance(data, dict):
                return False
            
            for token_key, token_data in data.items():
                required_fields = ['confluence_url', 'username', 'encrypted_token_data', 'created_at']
                if not all(field in token_data for field in required_fields):
                    return False
                
                # Проверяем структуру зашифрованных данных
                encrypted_data = token_data['encrypted_token_data']
                required_crypto_fields = ['encrypted_token', 'salt', 'algorithm', 'iterations']
                if not all(field in encrypted_data for field in required_crypto_fields):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка проверки целостности файла токенов: {e}")
            return False
    
    def _load_token_file(self) -> Dict[str, Any]:
        """Загружает файл с токенами"""
        if not self.config_path.exists():
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки файла токенов: {e}")
            return {}
    
    def _save_token_file(self, data: Dict[str, Any]):
        """Сохраняет файл с токенами"""
        try:
            # Создаем директорию если не существует
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Сохраняем с правильными правами доступа
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Устанавливаем права доступа только для владельца
            if os.name != 'nt':  # Не Windows
                os.chmod(self.config_path, 0o600)
                
        except Exception as e:
            raise EncryptionError(f"Ошибка сохранения файла токенов: {e}")
    
    def _generate_token_key(self, confluence_url: str, username: str) -> str:
        """Генерирует ключ для токена"""
        combined = f"{confluence_url}:{username}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _get_current_timestamp(self) -> str:
        """Возвращает текущую временную метку"""
        from datetime import datetime
        return datetime.utcnow().isoformat()


class ConfluenceTokenCLI:
    """CLI утилита для управления токенами Confluence"""
    
    def __init__(self, token_manager: ConfluenceTokenManager):
        """
        Инициализация CLI
        
        Args:
            token_manager: Менеджер токенов
        """
        self.token_manager = token_manager
    
    def add_token_interactive(self) -> bool:
        """
        Интерактивное добавление токена
        
        Returns:
            True если токен добавлен успешно
        """
        try:
            print("\n=== Добавление токена Confluence ===")
            
            confluence_url = input("URL Confluence (например, https://company.atlassian.net/wiki): ").strip()
            if not confluence_url:
                print("❌ URL не может быть пустым")
                return False
            
            username = input("Имя пользователя (email): ").strip()
            if not username:
                print("❌ Имя пользователя не может быть пустым")
                return False
            
            import getpass
            token = getpass.getpass("API токен: ").strip()
            if not token:
                print("❌ Токен не может быть пустым")
                return False
            
            password = getpass.getpass("Пароль для шифрования токена: ").strip()
            if not password:
                print("❌ Пароль не может быть пустым")
                return False
            
            password_confirm = getpass.getpass("Подтвердите пароль: ").strip()
            if password != password_confirm:
                print("❌ Пароли не совпадают")
                return False
            
            # Сохраняем токен
            success = self.token_manager.save_encrypted_token(
                token=token,
                password=password,
                confluence_url=confluence_url,
                username=username
            )
            
            if success:
                print("✅ Токен успешно сохранен")
                return True
            else:
                print("❌ Ошибка сохранения токена")
                return False
                
        except KeyboardInterrupt:
            print("\n❌ Операция отменена")
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def list_tokens(self):
        """Выводит список сохраненных токенов"""
        tokens = self.token_manager.list_saved_tokens()
        
        if not tokens:
            print("📝 Сохраненных токенов нет")
            return
        
        print("\n=== Сохраненные токены ===")
        for i, token_info in enumerate(tokens, 1):
            print(f"{i}. {token_info['username']}@{token_info['confluence_url']}")
            print(f"   Создан: {token_info['created_at']}")
            print(f"   Последнее использование: {token_info['last_used']}")
            print()
    
    def delete_token_interactive(self) -> bool:
        """
        Интерактивное удаление токена
        
        Returns:
            True если токен удален успешно
        """
        try:
            tokens = self.token_manager.list_saved_tokens()
            
            if not tokens:
                print("📝 Нет токенов для удаления")
                return False
            
            print("\n=== Удаление токена ===")
            self.list_tokens()
            
            choice = input("Введите номер токена для удаления (или 'q' для отмены): ").strip()
            
            if choice.lower() == 'q':
                print("❌ Операция отменена")
                return False
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(tokens):
                    token_info = tokens[index]
                    
                    confirm = input(f"Удалить токен для {token_info['username']}@{token_info['confluence_url']}? (y/N): ").strip()
                    
                    if confirm.lower() == 'y':
                        success = self.token_manager.delete_token(
                            confluence_url=token_info['confluence_url'],
                            username=token_info['username']
                        )
                        
                        if success:
                            print("✅ Токен успешно удален")
                            return True
                        else:
                            print("❌ Ошибка удаления токена")
                            return False
                    else:
                        print("❌ Операция отменена")
                        return False
                else:
                    print("❌ Неверный номер токена")
                    return False
                    
            except ValueError:
                print("❌ Неверный формат номера")
                return False
                
        except KeyboardInterrupt:
            print("\n❌ Операция отменена")
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False


def create_token_manager(config_path: Optional[str] = None) -> ConfluenceTokenManager:
    """
    Создает менеджер токенов
    
    Args:
        config_path: Путь к файлу конфигурации
        
    Returns:
        Настроенный менеджер токенов
    """
    if config_path is None:
        config_path = "confluence_tokens.json"
    
    return ConfluenceTokenManager(config_path)


def main():
    """Главная функция CLI"""
    import sys
    
    token_manager = create_token_manager()
    cli = ConfluenceTokenCLI(token_manager)
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python confluence_encryption.py add     - Добавить токен")
        print("  python confluence_encryption.py list    - Список токенов")
        print("  python confluence_encryption.py delete  - Удалить токен")
        print("  python confluence_encryption.py check   - Проверить целостность")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'add':
        cli.add_token_interactive()
    elif command == 'list':
        cli.list_tokens()
    elif command == 'delete':
        cli.delete_token_interactive()
    elif command == 'check':
        if token_manager.validate_token_file_integrity():
            print("✅ Файл токенов корректен")
        else:
            print("❌ Файл токенов поврежден")
    else:
        print(f"❌ Неизвестная команда: {command}")


if __name__ == '__main__':
    main()