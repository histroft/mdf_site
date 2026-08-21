import os
from pathlib import Path
from typing import Union, List, Optional
import img2pdf
import logging

logger = logging.getLogger(__name__)


def png_to_pdf(
    input_path: Union[str, Path, List[Union[str, Path]]],
    output_path: Union[str, Path],
    page_size: str = 'A4',
    fit: str = 'into',  # 'into', 'fill', 'shrink', 'exact'
    center: bool = True,
    border: tuple = (0, 0, 0, 0)  # top, right, bottom, left in mm
) -> bool:
    """
    Конвертирует PNG в PDF используя img2pdf
    
    Args:
        input_path: путь к PNG файлу или список путей (str или Path)
        output_path: путь для сохранения PDF (str или Path)
        page_size: размер страницы ('A4', 'Letter', 'A3', etc.)
        fit: как разместить изображение на странице
        center: центрировать изображение
        border: границы в мм (верх, право, низ, лево)
    
    Returns:
        bool: True если успешно
    """
    # ===== КОНВЕРТАЦИЯ PATH В СТРОКУ =====
    # Конвертируем input_path в строку или список строк
    if isinstance(input_path, Path):
        image_paths = [str(input_path)]
    elif isinstance(input_path, list):
        image_paths = [str(p) if isinstance(p, Path) else p for p in input_path]
    else:
        image_paths = [str(input_path)]
    
    # Конвертируем output_path в строку
    if isinstance(output_path, Path):
        output_path_str = str(output_path)
    else:
        output_path_str = output_path
    
    logger.info(f"📄 Конвертация PNG в PDF")
    logger.info(f"   Вход: {image_paths}")
    logger.info(f"   Выход: {output_path_str}")
    
    try:
        # Проверяем файлы
        valid_paths = []
        for img_path in image_paths:
            if not os.path.exists(img_path):
                logger.warning(f"   ⚠ Файл не найден: {img_path}")
                continue
            
            if not img_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                logger.warning(f"   ⚠ Неподдерживаемый формат: {img_path}")
                continue
            
            valid_paths.append(img_path)
        
        if not valid_paths:
            logger.error("   ❌ Нет изображений для конвертации")
            return False
        
        # Создаем директорию для выходного файла, если её нет
        output_dir = os.path.dirname(output_path_str)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Конвертируем
        pdf_data = None
        with open(output_path_str, "wb") as f:
            if len(valid_paths) == 1:
                # Один файл
                pdf_data = img2pdf.convert(
                    valid_paths[0],
                    pagesize=page_size,
                    fit=fit,
                    center=center,
                    border=border
                )
            else:
                # Несколько файлов
                pdf_data = img2pdf.convert(
                    valid_paths,
                    pagesize=page_size,
                    fit=fit,
                    center=center,
                    border=border
                )
            
            # Проверяем, что данные не None
            if pdf_data is None:
                logger.error("   ❌ img2pdf вернул None - возможно, проблема с изображением")
                return False
            
            # Записываем данные
            f.write(pdf_data)
        
        logger.info(f"   ✅ PDF сохранен: {output_path_str}")
        logger.info(f"      Страниц: {len(valid_paths)}")
        logger.info(f"      Размер страницы: {page_size}")
        logger.info(f"      Размер файла: {os.path.getsize(output_path_str) / 1024:.1f} KB")
        
        return True
        
    except img2pdf.ImageOpenError as e:
        logger.error(f"   ❌ Ошибка открытия изображения: {e}")
        return False
    except img2pdf.ImageSizeError as e:
        logger.error(f"   ❌ Ошибка размера изображения: {e}")
        return False
    except Exception as e:
        logger.error(f"   ❌ Ошибка конвертации: {type(e).__name__}: {e}")
        return False