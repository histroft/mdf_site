"""
Модуль для рисования простых фигур
"""
import logging

logger = logging.getLogger(__name__)


def draw_line_msp(msp, x1: float, y1: float, x2: float, y2: float,
                  color: int = 1, layer: str = "0"):
    """
    Рисует линию
    """
    attribs = {'color': color, 'layer': layer}
    return msp.add_line((x1, y1), (x2, y2), dxfattribs=attribs)


def draw_circle_msp(msp, x: float, y: float, radius: float,
                    color: int = 1, layer: str = "0"):
    """
    Рисует окружность
    """
    attribs = {'color': color, 'layer': layer}
    return msp.add_circle((x, y), radius=radius, dxfattribs=attribs)


def draw_rectangle_msp(msp, x: float, y: float, width: float, height: float,
                       color: int = 1, layer: str = "0"):
    """
    Рисует прямоугольник
    """
    draw_line_msp(msp, x, y, x + width, y, color, layer)
    draw_line_msp(msp, x + width, y, x + width, y + height, color, layer)
    draw_line_msp(msp, x + width, y + height, x, y + height, color, layer)
    draw_line_msp(msp, x, y + height, x, y, color, layer)