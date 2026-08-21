from flask import Flask
from flask_login import LoginManager, UserMixin
from config import Config

login_manager = LoginManager()

# Класс User для Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username
    
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя по ID"""
    from app.auth import load_users
    
    users = load_users()
    for username, user_data in users.items():
        if str(user_data['id']) == user_id:
            return User(user_data['id'], username)
    return None

def create_app():
    app = Flask(__name__)
    
    # Загружаем конфигурацию
    app.config.from_object(Config)
    
    # Создаем необходимые директории
    Config.ensure_directories()
    
    # Устанавливаем секретный ключ
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    
    login_manager.init_app(app)
    login_manager.login_view = 'main.index'
    
    # Регистрируем blueprints
    from app.routes import main_bp
    from app.auth import auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    
    return app