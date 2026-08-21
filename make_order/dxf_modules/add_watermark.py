from pathlib import Path
from typing import Union, List

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm
from reportlab.lib.colors import Color
import io
import logging

logger = logging.getLogger(__name__)


def add_watermark(
    input_pdf: Union[str, Path],
    output_pdf: Union[str, Path],
    watermark_text: str = "TOREX",
    opacity: float = 0.2,
    font_size: int = 40,
    color: tuple = (128, 128, 128),
    angle: int = 45,
    repeat: bool = True,  # Повторять водяной знак по всей странице
    spacing: int = 200  # Расстояние между повторяющимися знаками
) -> bool:
    """
    Добавляет водяной знак на всю страницу PDF
    
    Args:
        input_pdf: путь к исходному PDF
        output_pdf: путь для сохранения PDF с водяным знаком
        watermark_text: текст водяного знака
        opacity: прозрачность (0-1)
        font_size: размер шрифта
        color: цвет водяного знака (R, G, B)
        angle: угол поворота в градусах
        repeat: если True, заполняет всю страницу сеткой знаков
        spacing: расстояние между знаками (в пикселях)
    """
    try:
        # Конвертируем Path в строку
        if isinstance(input_pdf, Path):
            input_pdf = str(input_pdf)
        if isinstance(output_pdf, Path):
            output_pdf = str(output_pdf)
        
        # Определяем размер страницы из исходного PDF
        reader = PdfReader(input_pdf)
        if reader.pages:
            page = reader.pages[0]
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)
            pagesize = (page_width, page_height)
        else:
            pagesize = A4
            page_width, page_height = A4
        
        logger.info(f"   📄 Размер страницы: {page_width:.0f} x {page_height:.0f}")
        
        # Создаем водяной знак
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=pagesize)
        
        # Цвет с прозрачностью
        r, g, b = color
        can.setFillColor(Color(r/255, g/255, b/255, alpha=opacity))
        can.setFont("Helvetica-Bold", font_size)
        
        if repeat:
            # Создаем сетку водяных знаков по всей странице
            can.saveState()
            
            # Рассчитываем размер текста
            text_width = len(watermark_text) * font_size * 0.6
            text_height = font_size * 1.2
            
            # Шаг между знаками
            step_x = text_width + spacing
            step_y = text_height + spacing
            
            logger.info(f"   📐 Шаг сетки: X={step_x:.0f}, Y={step_y:.0f}")
            logger.info(f"   📝 Размер текста: {text_width:.0f} x {text_height:.0f}")
            
            # Создаем сетку, покрывающую всю страницу с запасом
            count = 0
            for x in range(-int(page_width), int(page_width * 2), int(step_x)):
                for y in range(-int(page_height), int(page_height * 2), int(step_y)):
                    can.saveState()
                    can.translate(x, y)
                    can.rotate(angle)
                    can.drawCentredString(0, 0, watermark_text)
                    can.restoreState()
                    count += 1
            
            logger.info(f"   🔄 Создано {count} водяных знаков")
            can.restoreState()
        else:
            # Один водяной знак по центру
            can.saveState()
            can.translate(page_width/2, page_height/2)
            can.rotate(angle)
            can.drawCentredString(0, 0, watermark_text)
            can.restoreState()
        
        can.save()
        
        # Создаем новый PDF с водяным знаком
        packet.seek(0)
        watermark_pdf = PdfReader(packet)
        
        # Добавляем водяной знак на каждую страницу
        writer = PdfWriter()
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            page.merge_page(watermark_pdf.pages[0])
            writer.add_page(page)
        
        # Сохраняем результат
        with open(output_pdf, 'wb') as f:
            writer.write(f)
        
        logger.info(f"   ✅ Водяной знак добавлен в PDF: {output_pdf}")
        return True
        
    except Exception as e:
        logger.error(f"   ❌ Ошибка добавления водяного знака: {e}")
        import traceback
        traceback.print_exc()
        return False