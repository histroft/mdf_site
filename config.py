import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

class Config:
    """Production конфигурация"""
    
    # Базовая директория
    BASE_DIR = Path(__file__).parent.absolute()
    
    # Директории
    DATA_DIR = BASE_DIR / 'database'
    ORDERS_DIR = BASE_DIR / 'orders'
    LOGS_DIR = BASE_DIR / 'logs'

    # WEB_NST читает каталог моделей из корня RENDER_NEW, а пользовательские
    # результаты хранит в собственном временном каталоге.
    MODULE_3D_DIR = Path(os.getenv(
        'MODULE_3D_DIR',
        str(BASE_DIR.parent / 'RENDER_NEW')
    ))
    RESULT_3D_DIR = Path(os.getenv('RESULT_3D_DIR', str(BASE_DIR / 'temp' / '3d-results')))
    RENDER_API_URL = os.getenv('RENDER_API_URL', 'http://127.0.0.1:5001').rstrip('/')
    RENDER_API_TOKEN = os.getenv('RENDER_API_TOKEN', '')
    RENDER_CONNECT_TIMEOUT = int(os.getenv('RENDER_CONNECT_TIMEOUT', '10'))
    # Больше серверного timeout: сюда входит ожидание очереди и скачивание ответа.
    RENDER_TIMEOUT = int(os.getenv('RENDER_TIMEOUT', '3600'))
    RENDER_DOWNLOAD_TIMEOUT = int(os.getenv('RENDER_DOWNLOAD_TIMEOUT', '120'))
    RENDER_MAX_IMAGE_BYTES = int(os.getenv('RENDER_MAX_IMAGE_BYTES', str(25 * 1024 * 1024)))
    # RESULT_3D_DIR.mkdir(parents=True, exist_ok=True) # Создается в ensure_directories
    
    # Сервер
    PORT = 5000
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    #XML
    XML = '/mnt/network_share/Assortment-TOREX-777.xml'
    PRICE = '/mnt/network_share/TOREX-Assortment-Prices.xml'
    BASE_PRICE_XML = '/mnt/network_share/Assortment-base-price-test.xml'
    ALL_PRICES_XML = '/mnt/network_share/Assortment-base-all-price-test.xml'
    
    # Базы данных
    DATABASE = os.getenv('DATABASE', str(DATA_DIR / 'doors.db'))
    MDF_DB = os.getenv('MDF_DB', str(DATA_DIR / 'mdf_pic.db'))
    PATH_TO_PRICE_DB = os.getenv('PATH_TO_PRICE_DB', str(DATA_DIR / 'price_database.db'))
    STATISTIC = os.getenv('STATISTIC', str(DATA_DIR / 'statistic.db'))
    NEW_PATH_TO_PRICE_DB = os.getenv('NEW_PATH_TO_PRICE_DB', str(DATA_DIR / 'new_price_database.db'))
    
    
    # Файл пользователей
    USERS_FILE = os.getenv('USERS_FILE', str(DATA_DIR / 'users.csv'))
    
    # Внешние ресурсы
    GOOGLE_URL = os.getenv('GOOGLE_URL', '')
    MDF_TABLE_URL = os.getenv('MDF_TABLE_URL', '')
    
    # Безопасность
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-jwt-secret-key-change-in-production')
    
    # Rate limiting
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'True').lower() == 'true'
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100/hour')
    
    # Логирование
    LOG_FILE = os.getenv('LOG_FILE', str(LOGS_DIR / 'server.log'))
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    
    # Настройки производительности
    BATCH_SIZE = {
        'base_prices': 5000,      # Размер пакета для базовых цен
        'options': 1000,          # Размер пакета для опций
    }

    # Настройки парсинга
    XML_ENCODING = 'utf-8'        # Кодировка XML файлов
    STREAMING_MODE = True         # Использовать потоковую обработку
    MEMORY_LIMIT_MB = 1024        # Лимит памяти в MB

    # Режимы обновления
    UPDATE_MODE = 'full'          # 'full' - полное обновление, 'incremental' - инкрементальное
        
    @classmethod
    def ensure_directories(cls):
        """Создает все необходимые директории"""
        dirs = [cls.DATA_DIR, cls.ORDERS_DIR, cls.LOGS_DIR, cls.RESULT_3D_DIR]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        print(f"✓ Директории созданы: {[str(d) for d in dirs]}")
    
    @classmethod
    def validate(cls):
        """Проверяет конфигурацию"""
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            print("⚠️ ВНИМАНИЕ: Используется DEV SECRET_KEY! Смените для production!")
        return True
