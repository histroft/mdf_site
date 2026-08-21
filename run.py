#!/usr/bin/env python
import sys
import os
from pathlib import Path


# Добавляем корень проекта в PATH
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from config import Config

app = create_app()
def clear_texture_cache():
    """Очищает кеш миниатюр текстур."""
    cache_dir = Config.BASE_DIR / 'temp' / 'texture_cache'
    if not cache_dir.exists():
        print("ℹ️  Кеш текстур не найден, очистка не требуется.")
        return

    import shutil
    shutil.rmtree(cache_dir)
    print(f"✅ Кеш текстур в '{cache_dir}' успешно очищен.")


if __name__ == '__main__':
    Config.ensure_directories()
    Config.validate()
    if Config.DEBUG:
        clear_texture_cache()
    
    print(f"\n{'='*50}")
    print(f"WEB NST Server Starting...")
    print(f"Port: {Config.PORT}")
    print(f"Debug: {Config.DEBUG}")
    print(f"Database: {Config.DATABASE}")
    print(f"{'='*50}\n")
    
    app.run(
        debug=Config.DEBUG,
        host='0.0.0.0',
        port=Config.PORT
    )