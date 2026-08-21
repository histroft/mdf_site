"""
Модули для работы с DXF файлами (упрощенная версия)
"""

# Экспортируем только то, что нужно пользователям
from make_order.dxf_modules.base import DXFDocument
from make_order.dxf_modules.inserting import insert_dxf
from make_order.dxf_modules.transforms import scale_msp, mirror_msp
from make_order.dxf_modules.primitives import draw_line_msp, draw_circle_msp, draw_rectangle_msp
from make_order.dxf_modules.text import add_text_msp, add_multiline_text_msp

__all__ = [
    'DXFDocument',
    'insert_dxf',
    'scale_msp',
    'mirror_msp',
    'draw_line_msp',
    'draw_circle_msp',
    'draw_rectangle_msp',
    'add_text_msp',
    'add_multiline_text_msp'
]