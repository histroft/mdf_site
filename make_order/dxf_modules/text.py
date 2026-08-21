"""
Модуль для работы с текстом
"""
import logging
from ezdxf.math import Vec3

logger = logging.getLogger(__name__)


def add_text_msp(msp, text: str, x: float, y: float, height: float = 10,
                 rotation: float = 0, color: int = 1, layer: str = "0",
                 style: str = "STANDARD"):
    """Добавляет текст с поворотом"""
    attribs = {
        'height': height,
        'insert': (x, y, 0),
        'rotation': rotation,
        'color': color,
        'layer': layer,
        'style': style
    }
    return msp.add_text(text, dxfattribs=attribs)


def add_multiline_text_msp(msp, lines: list, x: float, y: float, height: float = 10,
                           line_spacing: float = 1.5, **kwargs):
    """
    Добавляет многострочный текст
    """
    texts = []
    for i, line in enumerate(lines):
        y_offset = y - i * height * line_spacing
        text = add_text_msp(msp, line, x, y_offset, height=height, **kwargs)
        texts.append(text)
    return texts