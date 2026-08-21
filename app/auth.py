
from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_user, logout_user
import csv
import os
import scrypt
import hashlib
from config import Config

auth_bp = Blueprint('auth', __name__)

def verify_password_pbkdf2(stored_hash, password):
    """Проверяет пароль против pbkdf2 хеша"""
    try:
        if not stored_hash.startswith('pbkdf2:'):
            return False
        
        hash_part = stored_hash[7:]
        parts = hash_part.split('$')
        
        if len(parts) != 3:
            return False
        
        params = parts[0].split(':')
        if len(params) != 2:
            return False
        
        algorithm = params[0]
        iterations = int(params[1])
        salt = parts[1]
        stored_key = parts[2]
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations,
            dklen=32
        )
        
        generated_key = key.hex()
        return generated_key == stored_key
        
    except Exception as e:
        print(f"Error in verify_password_pbkdf2: {e}")
        return False

def verify_password_scrypt(stored_hash, password):
    """Проверяет пароль против scrypt хеша"""
    try:
        if not stored_hash.startswith('scrypt:'):
            return False
        
        hash_parts = stored_hash[7:].split('$')
        if len(hash_parts) != 3:
            return False
        
        params = hash_parts[0].split(':')
        if len(params) != 3:
            return False
        
        N = int(params[0])
        r = int(params[1])
        p = int(params[2])
        salt = hash_parts[1].encode('utf-8')
        stored_key = bytes.fromhex(hash_parts[2])
        
        generated_key = scrypt.hash(password, salt, N=N, r=r, p=p, buflen=64)
        
        return generated_key == stored_key
        
    except Exception as e:
        print(f"Error in verify_password_scrypt: {e}")
        return False

def verify_password(stored_hash, password):
    """Универсальная проверка пароля (поддерживает pbkdf2 и scrypt)"""
    if stored_hash.startswith('pbkdf2:'):
        return verify_password_pbkdf2(stored_hash, password)
    elif stored_hash.startswith('scrypt:'):
        return verify_password_scrypt(stored_hash, password)
    else:
        return False

def load_users():
    """Загружает пользователей из CSV файла"""
    users = {}
    users_file = Config.USERS_FILE
    
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for idx, row in enumerate(reader, start=1):
                    if len(row) >= 2:
                        username = row[0].strip()
                        password_hash = row[1].strip()
                        users[username] = {
                            'password_hash': password_hash,
                            'id': idx
                        }
        except Exception as e:
            print(f"Error loading users: {e}")
            return {}
    
    return users

@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Введите логин и пароль', 'error')
        return redirect(url_for('main.index'))
    
    users = load_users()
    
    if username in users:
        stored_hash = users[username]['password_hash']
        
        if verify_password(stored_hash, password):
            from app import User
            user = User(users[username]['id'], username)
            login_user(user)
            flash('Вход выполнен успешно', 'success')
            return redirect(url_for('main.dashboard'))
    
    flash('Неверный логин или пароль', 'error')
    return redirect(url_for('main.index'))

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.index'))
