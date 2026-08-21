"""
Декораторы для защиты эндпоинтов
Поддерживает как Bearer токены (JWT), так и Basic Auth для обратной совместимости
"""

from functools import wraps
from flask import request, jsonify, current_app
import jwt
import base64
from typing import Optional, Dict, Callable
import logging

from auth.users import authenticate_user

logger = logging.getLogger(__name__)


def authenticate_basic(auth_header: str) -> Optional[Dict]:
    """
    Проверка Basic Auth
    
    Args:
        auth_header: заголовок Authorization
        
    Returns:
        Optional[Dict]: данные пользователя в формате {'username': str, 'is_admin': bool}
    """
    try:
        if not auth_header.startswith('Basic '):
            return None
        
        auth_type, credentials = auth_header.split(' ', 1)
        decoded = base64.b64decode(credentials).decode('utf-8')
        username, password = decoded.split(':', 1)
        
        # Используем функцию аутентификации из users.py
        user = authenticate_user(current_app.config['USERS_FILE'], username, password)
        
        if user:
            logger.info(f"Basic Auth successful for user: {username}")
            # Убеждаемся, что возвращаем единую структуру
            return {
                'username': username,
                'is_admin': user.get('is_admin', False)
            }
        else:
            logger.warning(f"Basic Auth failed for user: {username}")
            return None
            
    except Exception as e:
        logger.error(f"Error in Basic Auth: {e}")
        return None


def authenticate_bearer(auth_header: str) -> Optional[Dict]:
    """
    Проверка Bearer токена (JWT)
    
    Args:
        auth_header: заголовок Authorization
        
    Returns:
        Optional[Dict]: данные пользователя в формате {'username': str, 'is_admin': bool}
    """
    try:
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        payload = jwt.decode(
            token, 
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        
        logger.info(f"Bearer Auth successful for user: {payload.get('username')}")
        
        # Преобразуем payload в единую структуру
        return {
            'username': payload.get('username'),
            'is_admin': payload.get('is_admin', False)
        }
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in Bearer Auth: {e}")
        return None


def get_token_from_header() -> Optional[str]:
    """
    Получение токена из заголовка Authorization
    
    Returns:
        Optional[str]: токен или None
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return None
    
    if auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    return None


def get_username_safe() -> str:
    """
    Безопасно получает имя пользователя из request.user
    
    Returns:
        str: имя пользователя или 'Unknown'
    """
    if not hasattr(request, 'user') or request.user is None:
        return 'Unknown'
    
    if isinstance(request.user, dict):
        return request.user.get('username', 'Unknown')
    
    return str(request.user)


def auth_required(f: Callable) -> Callable:
    """
    Декоратор для защиты эндпоинтов
    Поддерживает как Bearer токены, так и Basic Auth
    
    Пример использования:
        @app.route('/protected')
        @auth_required
        def protected_route():
            return jsonify({'user': request.user})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Требуется авторизация'}), 401
        
        # Пробуем аутентификацию по Bearer токену (JWT)
        user = authenticate_bearer(auth_header)
        
        # Если не получилось, пробуем Basic Auth
        if not user:
            user = authenticate_basic(auth_header)
        
        if not user:
            return jsonify({'error': 'Неверные учетные данные'}), 401
        
        # Сохраняем пользователя в request для использования в эндпоинте
        request.user = user
        return f(*args, **kwargs)
    
    return decorated


def admin_required(f: Callable) -> Callable:
    """
    Декоратор для эндпоинтов, требующих прав администратора
    """
    @wraps(f)
    @auth_required
    def decorated(*args, **kwargs):
        user = getattr(request, 'user', {})
        if not user.get('is_admin', False):
            return jsonify({'error': 'Требуются права администратора'}), 403
        return f(*args, **kwargs)
    
    return decorated


def optional_auth(f: Callable) -> Callable:
    """
    Декоратор для необязательной авторизации
    Если токен есть - пользователь будет в request.user
    Если нет - request.user будет None
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        request.user = None
        
        if auth_header:
            # Пробуем Bearer токен
            user = authenticate_bearer(auth_header)
            if not user:
                # Пробуем Basic Auth
                user = authenticate_basic(auth_header)
            request.user = user
        
        return f(*args, **kwargs)
    
    return decorated