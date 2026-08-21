import logging
import re
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)

def natural_sort_key(s):
    """
    Ключ для "естественной" сортировки строк (например, "Стена 10" будет после "Стена 2").
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def get_dynamic_scene_textures() -> tuple[list, list]:
    """
    Сканирует директорию 'decor' и возвращает списки доступных текстур
    для стен и полов в формате, подходящем для шаблона.
    """
    decor_dir = Config.MODULE_3D_DIR / 'decor'
    if not decor_dir.is_dir():
        logger.warning(f"Директория с текстурами окружения не найдена: {decor_dir}")
        return [], []

    walls = []
    floors = []

    for f in decor_dir.iterdir():
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            name = f.stem.replace('wall', 'Стена ').replace('floor', 'Пол ').capitalize()
            relative_path = f.relative_to(Config.MODULE_3D_DIR).as_posix()
            
            if f.stem.startswith('wall'):
                walls.append((relative_path, name))
            elif f.stem.startswith('floor'):
                floors.append((relative_path, name))

    # Сортируем списки для предсказуемого порядка в интерфейсе
    sorted_walls = sorted(walls, key=lambda x: natural_sort_key(x[1]))
    sorted_floors = sorted(floors, key=lambda x: natural_sort_key(x[1]))

    return sorted_walls, sorted_floors

def get_scene_assets() -> set[str]:
    """
    Возвращает множество всех допустимых путей к текстурам окружения
    для валидации.
    """
    walls, floors = get_dynamic_scene_textures()
    wall_paths = {item[0] for item in walls}
    floor_paths = {item[0] for item in floors}
    return wall_paths.union(floor_paths)