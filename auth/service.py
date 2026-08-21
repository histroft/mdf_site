import csv
import jwt
import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from flask import current_app
from typing import Optional, Dict

class AuthService:
    def __init__(self, users_file: str):
        self.users_file = users_file
        
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """Аутентификация пользователя"""
        users = self._load_users()
        
        if username in users and check_password_hash(users[username]['password'], password):
            return {
                'username': username,
                'is_admin': users[username].get('is_admin', False)
            }
        return None
    
    def generate_token(self, user_data: Dict) -> str:
        """Генерация JWT токена"""
        payload = {
            'username': user_data['username'],
            'is_admin': user_data.get('is_admin', False),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(
                seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
            )
        }
        return jwt.encode(
            payload, 
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
    
    def _load_users(self) -> Dict:
        """Загрузка пользователей из CSV"""
        users = {}
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    users[row['username']] = {
                        'password': row['password'],
                        'is_admin': row.get('is_admin', 'false').lower() == 'true'
                    }
        except FileNotFoundError:
            # Создаем файл с тестовым пользователем
            self._create_default_user()
            return self._load_users()
        return users
    
    def _create_default_user(self):
        """Создание пользователя по умолчанию"""
        with open(self.users_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'password', 'is_admin'])
            writer.writerow([
                'admin',
                generate_password_hash('admin123'),
                'true'
            ])