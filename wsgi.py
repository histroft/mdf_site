import sys
import os
from pathlib import Path

# Добавляем корень проекта в PATH, чтобы импорты работали корректно
# Это делает скрипт независимым от того, откуда он запускается.
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("\nОшибка: Этот файл (wsgi.py) не предназначен для прямого запуска.")
    print("Для запуска сервера в режиме разработки используйте 'python run.py'")
    print("Для production используйте Gunicorn, как настроено в 'manage.sh'.\n")