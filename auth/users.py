"""
Модуль для работы с пользователями
"""

import csv
import jwt
import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from typing import Optional, Dict
import logging
import os

logger = logging.getLogger(__name__)


def authenticate_user(users_file: str, username: str, password: str) -> Optional[Dict]:
    """
    Аутентификация пользователя
    
    Args:
        users_file: путь к CSV файлу с пользователями
        username: имя пользователя
        password: пароль
        
    Returns:
        Optional[Dict]: данные пользователя или None
    """
    try:
        users = _load_users(users_file)
        
        if username in users and check_password_hash(users[username]['password'], password):
            logger.info(f"Успешная аутентификация пользователя: {username}")
            return {
                'username': username,
                'is_admin': users[username].get('is_admin', False)
            }
        else:
            logger.warning(f"Неудачная попытка входа: {username}")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка аутентификации: {e}")
        return None


def generate_token(user_data: Dict, secret_key: str, expires_in: int) -> str:
    """
    Генерация JWT токена
    
    Args:
        user_data: данные пользователя
        secret_key: секретный ключ для подписи
        expires_in: время жизни токена в секундах
        
    Returns:
        str: JWT токен
    """
    payload = {
        'username': user_data['username'],
        'is_admin': user_data.get('is_admin', False),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
    }
    
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


def add_user(users_file: str, username: str, password: str, is_admin: bool = False) -> bool:
    """
    Добавление нового пользователя
    
    Args:
        users_file: путь к CSV файлу
        username: имя пользователя
        password: пароль
        is_admin: права администратора
        
    Returns:
        bool: True если пользователь добавлен
    """
    try:
        # Проверяем, существует ли файл
        file_exists = os.path.exists(users_file) and os.path.getsize(users_file) > 0
        
        # Проверяем, не существует ли уже такой пользователь
        if file_exists:
            with open(users_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['username'] == username:
                        logger.warning(f"Пользователь {username} уже существует")
                        return False
        
        # Хешируем пароль
        hashed_password = generate_password_hash(password)
        
        # Добавляем пользователя
        with open(users_file, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['username', 'password', 'is_admin']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'username': username,
                'password': hashed_password,
                'is_admin': str(is_admin).lower()
            })
        
        logger.info(f"Пользователь {username} успешно добавлен")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка добавления пользователя: {e}")
        return False


def _load_users(users_file: str) -> Dict:
    """
    Загрузка пользователей из CSV файла
    
    Args:
        users_file: путь к CSV файлу
        
    Returns:
        Dict: словарь пользователей {username: data}
    """
    users = {}
    
    if not os.path.exists(users_file):
        logger.warning(f"Файл пользователей не найден: {users_file}")
        return users
    
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users[row['username']] = {
                    'password': row['password'],
                    'is_admin': row.get('is_admin', 'false').lower() == 'true'
                }
    except Exception as e:
        logger.error(f"Ошибка загрузки пользователей: {e}")
    
    return users


def create_default_admin(users_file: str):
    """
    Создание администратора по умолчанию, если файл пользователей не существует
    
    Args:
        users_file: путь к CSV файлу
    """
    if not os.path.exists(users_file):
        logger.info("Создание администратора по умолчанию (admin/admin123)")
        add_user(users_file, 'admin', 'admin123', is_admin=True)


# Для тестирования
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Тест создания пользователя
    test_file = 'test_users.csv'
    add_user(test_file, 'testuser', 'password123', is_admin=False)
    
    # Тест аутентификации
    user = authenticate_user(test_file, 'testuser', 'password123')
    print(f"Аутентификация: {user}")
    
    # Тест генерации токена
    if user:
        token = generate_token(user, 'secret', 3600)
        print(f"Токен: {token}")
    
    # Удаляем тестовый файл
    if os.path.exists(test_file):
        os.remove(test_file)