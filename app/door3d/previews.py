import logging
from pathlib import Path
import os
from typing import Optional
from urllib.parse import unquote_plus
from PIL import Image

from config import Config

logger = logging.getLogger(__name__)


def resolve_scene_texture(asset_path: str) -> Path:
    """
    Проверяет и возвращает путь к текстуре сцены (стены/пол).
    Здесь логика остаётся прежней, так как crosswalk.json не используется для сцен.
    """
    if not asset_path or '..' in asset_path:
        raise ValueError("Недопустимый путь к ассету")

    # Путь к текстурам сцены внутри папки RENDER_NEW
    base_path = Config.MODULE_3D_DIR
    full_path = (base_path / asset_path).resolve()

    # Проверка, что путь находится внутри разрешенной директории
    if base_path not in full_path.parents:
        raise ValueError("Попытка доступа за пределы разрешенной директории")

    if not full_path.is_file():
        raise FileNotFoundError(f"Файл текстуры сцены не найден: {full_path}")

    return full_path


def resolve_finish_texture(name: str) -> Path:
    """
    Формирует путь к файлу текстуры отделки по имени.
    Поиск ведется сначала в 'pvc_color', затем в 'metal_color'.
    """
    if not name:
        raise ValueError("Имя отделки не может быть пустым")
    
    # Декодируем имя из URL-формата (например, 'ПВХ+Дуб' -> 'ПВХ Дуб')
    normalized_name = unquote_plus(name)
    logger.info(f"Начинаем поиск текстуры. Оригинал: '{name}', Нормализовано: '{normalized_name}'")
    
    # Директории для поиска в порядке приоритета
    search_dirs = ["pvc_color", "metal_color"]

    for color_dir in search_dirs:
        logger.info(f"Ищем в директории: {color_dir}")
        possible_relative_paths = [
            Path("textures") / color_dir / normalized_name / f"{normalized_name}_BaseColor.png",
            Path("textures") / color_dir / normalized_name / f"{normalized_name}.png",
            Path("textures") / color_dir / normalized_name / f"{normalized_name}.jpg",
        ]

        for rel_path in possible_relative_paths:
            full_path = Config.MODULE_3D_DIR / rel_path
            if full_path.is_file():
                logger.info(f"✅ Текстура для '{normalized_name}' найдена по пути: {full_path}")
                return full_path
            
    # Если ничего не найдено после всех попыток
    logger.warning(f"Текстура для '{normalized_name}' не найдена ни по одному из правил. Поиск будет продолжен RENDER_NEW.")
    # Возвращаем оригинальное имя, чтобы RENDER_NEW попробовал найти его сам
    return Path(name)


def resolve_door_design_preview(name: str) -> Path:
    """Возвращает изображение-превью выбранного рисунка двери.

    Изображения хранятся в ``images/<название рисунка>/pic.png``. Для
    рисунков с вариантом отделки или стороной открывания используем базовое
    имя: например, ``Batista VM/ШП Каррара`` → ``Batista VM``,
    ``Arietta-R`` → ``Arietta``.
    """
    normalized_name = unquote_plus(name).strip()
    if not normalized_name:
        raise ValueError("Название рисунка не может быть пустым")

    base_name = normalized_name.split('/', maxsplit=1)[0].strip()
    candidate_names = [normalized_name]
    if base_name not in candidate_names:
        candidate_names.append(base_name)
    if base_name.endswith('-R'):
        candidate_names.append(base_name[:-2])

    images_root = (Config.MODULE_3D_DIR / "images").resolve()
    for candidate_name in candidate_names:
        source_path = (images_root / candidate_name / "pic.png").resolve()
        try:
            source_path.relative_to(images_root)
        except ValueError as exc:
            raise ValueError("Недопустимое название рисунка") from exc
        if source_path.is_file():
            return source_path

    raise FileNotFoundError(f"Превью рисунка не найдено: {normalized_name}")


def thumbnail_path(source_path: Path) -> Path:
    """Возвращает путь к кешированной миниатюре для указанного исходного файла."""
    cache_dir = Config.BASE_DIR / 'temp' / 'texture_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем имя файла на основе хеша пути, чтобы избежать конфликтов
    import hashlib
    filename = hashlib.md5(str(source_path).encode()).hexdigest() + ".webp"
    preview_path = cache_dir / filename

    # --- РЕШЕНИЕ: Создаем миниатюру, если она отсутствует ---
    if not preview_path.exists():
        logger.info(f"Миниатюра не найдена в кеше, создаем новую: {preview_path}")
        try:
            with Image.open(source_path) as img:
                # Уменьшаем до разумного размера для превью
                img.thumbnail((512, 512))
                # Сохраняем в формате WebP с хорошим качеством
                img.save(preview_path, 'webp', quality=85)
            logger.info(f"✅ Миниатюра успешно создана: {preview_path}")
        except Exception as e:
            logger.error(f"❌ Не удалось создать миниатюру для {source_path}: {e}")
            raise FileNotFoundError(f"Ошибка создания миниатюры для {source_path}")

    return preview_path
