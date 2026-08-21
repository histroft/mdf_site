import math
import os
import re
import matplotlib
matplotlib.use('Agg')

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import ezdxf


def dxf_to_jpg(dxf_filepath, png_filepath=None, dpi=300):
    """
    Конвертирует DXF в PNG с обрезкой пустого пространства
    """
    if png_filepath is None:
        base = os.path.splitext(dxf_filepath)[0]
        png_filepath = base + '.png'
    
    if not os.path.exists(dxf_filepath):
        print(f"❌ Файл не найден: {dxf_filepath}")
        return None
    
    result = render_dxf_with_fixed_text(dxf_filepath, png_filepath, dpi)
    
    if result and os.path.exists(result):
        # Обрезаем изображение
        result = trim_png(result)
        size_kb = os.path.getsize(result) / 1024
        print(f"📏 Размер: {size_kb:.1f} KB")
    else:
        print("❌ КОНВЕРТАЦИЯ НЕ УДАЛАСЬ")
    
    return result


def trim_png(png_path, keep_margin=75):
    """
    Обрезает пустое пространство вокруг изображения, но оставляет поля
    keep_margin - сколько пикселей поля оставить (в пикселях)
    """
    try:
        from PIL import Image, ImageChops
        
        img = Image.open(png_path)
        
        # Конвертируем в RGB если нужно
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        
        # Находим границы
        bg = Image.new(img.mode, img.size, (255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        
        if bbox:
            # Добавляем отступ (не обрезаем полностью)
            left = max(0, bbox[0] - keep_margin)
            top = max(0, bbox[1] - keep_margin)
            right = min(img.width, bbox[2] + keep_margin)
            bottom = min(img.height, bbox[3] + keep_margin)
            
            img_cropped = img.crop((left, top, right, bottom))
            img_cropped.save(png_path, 'PNG', optimize=True)
            print(f"   ✂️ Изображение обрезано с отступом {keep_margin}px: {right-left}x{bottom-top}")
        else:
            print(f"   ⚠ Не удалось определить границы")
        
        return png_path
        
    except Exception as e:
        print(f"   ⚠ Ошибка обрезки: {e}")
        return png_path



def render_dxf_with_fixed_text(dxf_filepath, png_filepath, dpi):
    """
    Рендеринг DXF с правильной обработкой текста
    """
    try:
        print("🔄 Загрузка DXF...")
        
        # Загружаем DXF
        try:
            doc = ezdxf.readfile(dxf_filepath) # type: ignore
            
        except Exception as e:
            print(f"❌ Ошибка загрузки DXF: {e}")
            return None
        
        msp = doc.modelspace()
        
        # Получаем границы чертежа для масштабирования
        bounds = get_drawing_bounds(msp)
        print(f"📏 Границы чертежа: {bounds}")
        
        # Создаем фигуру с правильным масштабом
        fig, ax = create_scaled_figure(bounds)
        
        # Рендерим все объекты
        stats = render_with_proper_scaling(msp, ax, bounds)
        
        # Сохраняем
        return save_figure_with_quality(fig, png_filepath, dpi, stats)
        
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_drawing_bounds(msp):
    """Получает границы чертежа для правильного масштабирования"""
    all_x = []
    all_y = []
    
    for entity in msp:
        try:
            dxftype = entity.dxftype()
            
            if dxftype == 'LINE':
                all_x.extend([entity.dxf.start[0], entity.dxf.end[0]])
                all_y.extend([entity.dxf.start[1], entity.dxf.end[1]])
                
            elif dxftype == 'CIRCLE':
                x, y = entity.dxf.center[0], entity.dxf.center[1]
                r = entity.dxf.radius
                all_x.extend([x - r, x + r])
                all_y.extend([y - r, y + r])
                
            elif dxftype == 'ARC':
                x, y = entity.dxf.center[0], entity.dxf.center[1]
                r = entity.dxf.radius
                all_x.extend([x - r, x + r])
                all_y.extend([y - r, y + r])
                
            elif dxftype == 'ELLIPSE':
                x, y = entity.dxf.center[0], entity.dxf.center[1]
                major = entity.dxf.major_axis
                major_len = math.sqrt(major[0]**2 + major[1]**2)
                minor_len = major_len * entity.dxf.ratio
                all_x.extend([x - major_len, x + major_len])
                all_y.extend([y - minor_len, y + minor_len])
                
            elif dxftype == 'LWPOLYLINE':
                points = list(entity.get_points())
                if points:
                    all_x.extend([p[0] for p in points])
                    all_y.extend([p[1] for p in points])
                    
            elif dxftype in ['TEXT', 'MTEXT']:
                if hasattr(entity.dxf, 'insert'):
                    all_x.append(entity.dxf.insert[0])
                    all_y.append(entity.dxf.insert[1])
                    
        except:
            continue
    
    if all_x and all_y:
        xmin, xmax = min(all_x), max(all_x)
        ymin, ymax = min(all_y), max(all_y)
        
        # Добавляем отступ 10%
        width = xmax - xmin
        height = ymax - ymin
        padding = max(width, height) * 0.1
        
        return {
            'xmin': xmin - padding,
            'xmax': xmax + padding,
            'ymin': ymin - padding,
            'ymax': ymax + padding,
            'width': width + 2 * padding,
            'height': height + 2 * padding
        }
    else:
        # Стандартные границы
        return {
            'xmin': 0, 'xmax': 1000,
            'ymin': 0, 'ymax': 1000,
            'width': 1000, 'height': 1000
        }


def create_scaled_figure(bounds):
    """Создает фигуру с правильным масштабом"""
    # Определяем размер фигуры в дюймах
    max_inches = 20
    
    if bounds['width'] > 0 and bounds['height'] > 0:
        scale_x = max_inches / bounds['width']
        scale_y = max_inches / bounds['height']
        scale = min(scale_x, scale_y)
        
        fig_width = bounds['width'] * scale
        fig_height = bounds['height'] * scale
    else:
        fig_width, fig_height = 20, 20
    
    print(f"🖼 Размер фигуры: {fig_width:.1f} × {fig_height:.1f} дюймов")
    
    # Создаем фигуру
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=100)
    
    # Устанавливаем границы
    ax.set_xlim(bounds['xmin'], bounds['xmax'])
    ax.set_ylim(bounds['ymin'], bounds['ymax'])
    
    # Белый фон
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    
    # Скрываем оси
    ax.set_axis_off()
    
    # Одинаковый масштаб
    ax.set_aspect('equal', adjustable='box')
    
    return fig, ax


def render_with_proper_scaling(msp, ax, bounds):
    """Рендерит объекты с правильным масштабированием"""
    stats = {
        'lines': 0, 'circles': 0, 'arcs': 0, 'ellipses': 0,
        'polylines': 0, 'texts': 0, 'mtexts': 0
    }
    
    # Масштабный коэффициент для текста
    scale_factor = 0.28
    print(f"📐 Масштабный коэффициент для текста: {scale_factor:.3f}")
    
    for entity in msp:
        try:
            dxftype = entity.dxftype()
            
            if dxftype == 'LINE':
                render_scaled_line(entity, ax)
                stats['lines'] += 1
                
            elif dxftype == 'CIRCLE':
                render_scaled_circle(entity, ax)
                stats['circles'] += 1
                
            elif dxftype == 'ARC':
                render_scaled_arc(entity, ax)
                stats['arcs'] += 1
                
            elif dxftype == 'ELLIPSE':
                render_scaled_ellipse(entity, ax)
                stats['ellipses'] += 1
                
            elif dxftype == 'LWPOLYLINE':
                render_scaled_polyline(entity, ax)
                stats['polylines'] += 1
                
            elif dxftype == 'TEXT':
                render_scaled_text(entity, ax, scale_factor)
                stats['texts'] += 1
                
            elif dxftype == 'MTEXT':
                render_scaled_mtext(entity, ax, scale_factor)
                stats['mtexts'] += 1
                
        except Exception as e:
            # Пропускаем проблемные объекты
            continue
    
    print(f"✅ Нарисовано объектов: {sum(stats.values())}")
    for obj_type, count in stats.items():
        if count > 0:
            print(f"   {obj_type}: {count}")
    
    return stats


def render_scaled_line(entity, ax):
    """Рисует линию"""
    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
        x1, y1 = entity.dxf.start[0], entity.dxf.start[1]
        x2, y2 = entity.dxf.end[0], entity.dxf.end[1]
        ax.plot([x1, x2], [y1, y2], 
                color='black',
                linewidth=0.5,
                solid_capstyle='round')




def render_scaled_circle(entity, ax):
    """Рисует круг"""
    if hasattr(entity.dxf, 'center') and hasattr(entity.dxf, 'radius'):
        x, y = entity.dxf.center[0], entity.dxf.center[1]
        r = entity.dxf.radius
        circle = plt.Circle((x, y), r, # type: ignore
                           color='black',
                           fill=False,
                           linewidth=0.5)
        ax.add_patch(circle)


def render_scaled_arc(entity, ax):
    """Рисует дугу"""
    if hasattr(entity.dxf, 'center') and hasattr(entity.dxf, 'radius'):
        x, y = entity.dxf.center[0], entity.dxf.center[1]
        r = entity.dxf.radius
        start_angle = getattr(entity.dxf, 'start_angle', 0)
        end_angle = getattr(entity.dxf, 'end_angle', 360)
        
        # Обработка отрицательных углов
        if end_angle < 0:
            end_angle = 360 + end_angle
        
        arc = patches.Arc((x, y), 2 * r, 2 * r,
                         angle=0,
                         theta1=start_angle,
                         theta2=end_angle,
                         color='black',
                         linewidth=0.5)
        ax.add_patch(arc)


def render_scaled_ellipse(entity, ax):
    """Рисует эллиптическую дугу"""
    try:
        center = entity.dxf.center
        major_axis = entity.dxf.major_axis
        ratio = entity.dxf.ratio
        
        # Параметры дуги
        start_param = getattr(entity.dxf, 'start_param', 0)
        end_param = getattr(entity.dxf, 'end_param', 2 * math.pi)
        
        # Конвертируем параметры в градусы
        start_angle = math.degrees(start_param)
        end_angle = math.degrees(end_param)
        
        # Длина большой полуоси
        major_length = math.sqrt(major_axis[0]**2 + major_axis[1]**2)
        # Угол поворота в градусах
        angle = math.degrees(math.atan2(major_axis[1], major_axis[0]))
        
        # Создаем эллиптическую дугу
        arc = patches.Arc(
            (center[0], center[1]),
            width=major_length * 2,
            height=major_length * ratio * 2,
            angle=angle,
            theta1=start_angle,
            theta2=end_angle,
            edgecolor='black',
            facecolor='none',
            linewidth=0.5
        )
        
        ax.add_patch(arc)
        
    except Exception as e:
        print(f"Ошибка отрисовки эллипса: {e}")


def render_scaled_polyline(entity, ax):
    """Рисует полилинию"""
    try:
        points = list(entity.get_points())
        if len(points) < 2:
            return
        
        # Просто рисуем точки последовательно
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        
        # Замыкаем если нужно
        is_closed = entity.closed if hasattr(entity, 'closed') else False
        if is_closed and len(points) > 2:
            xs.append(xs[0])
            ys.append(ys[0])
        
        ax.plot(xs, ys, color='black', linewidth=0.5)
        
    except Exception as e:
        print(f"Ошибка в render_scaled_polyline: {e}")


def render_scaled_text(entity, ax, scale_factor):
    """Рисует обычный текст с правильным масштабом и стилем"""
    if not hasattr(entity.dxf, 'insert'):
        return
    
    x, y = entity.dxf.insert[0], entity.dxf.insert[1]
    text_content = getattr(entity.dxf, 'text', '').strip()
    
    if not text_content:
        return
    
    # Получаем высоту текста
    height_dxf = getattr(entity.dxf, 'height', 10)
    font_size = height_dxf * scale_factor
    font_size = max(font_size, 6)
    font_size = min(font_size, 72)
    
    # ✅ Определяем стиль шрифта по имени стиля
    font_weight = 'normal'
    font_style = 'normal'
    
    if hasattr(entity.dxf, 'style'):
        style_name = entity.dxf.style
        if style_name:
            # Если стиль содержит BOLD - делаем жирным
            if 'BOLD' in style_name.upper():
                font_weight = 'bold'
            # Если стиль содержит ITALIC - делаем курсивом
            if 'ITALIC' in style_name.upper():
                font_style = 'italic'
    
    # Поворот
    rotation = getattr(entity.dxf, 'rotation', 0)
    
    # Выравнивание
    hjust, vjust = get_text_alignment_fixed(entity)
    
    # Рисуем текст с учётом стиля
    ax.text(x, y, text_content,
           color='black',
           fontsize=font_size,
           fontweight=font_weight,      # ✅ жирный для BOLD_TEXT
           fontstyle=font_style,        # ✅ курсив для ITALIC_TEXT
           rotation=rotation,
           rotation_mode='anchor',
           ha=hjust,
           va=vjust)


def render_scaled_mtext(entity, ax, scale_factor):
    """Рисует многострочный текст с переносами строк"""
    if not hasattr(entity.dxf, 'insert'):
        return
    
    x, y = entity.dxf.insert[0], entity.dxf.insert[1]
    raw_text = getattr(entity.dxf, 'text', '').strip()
    
    if not raw_text:
        return
    
    # Очищаем и обрабатываем текст
    text_content = process_mtext_with_newlines(raw_text)
    
    if not text_content.strip():
        return
    
    # Высота символов
    char_height = getattr(entity.dxf, 'char_height', 
                         getattr(entity.dxf, 'height', 10))
    
    # Преобразуем высоту
    font_size = char_height * scale_factor
    font_size = max(font_size, 6)
    font_size = min(font_size, 72)
    
    # Поворот
    rotation = getattr(entity.dxf, 'rotation', 0)
    
    # Выравнивание для MTEXT
    attachment_point = getattr(entity.dxf, 'attachment_point', 1)
    hjust, vjust = get_mtext_alignment_fixed(attachment_point)
    
    # Свойства шрифта из форматирования
    font_weight, font_style = extract_font_properties_fixed(raw_text)
    
    # Для многострочного текста используем параметр linespacing
    linespacing = getattr(entity.dxf, 'line_spacing_factor', 1.5)
    
    # Рисуем текст с переносами строк
    ax.text(x, y, text_content,
           color='black',
           fontsize=font_size,
           fontweight=font_weight,
           fontstyle=font_style,
           rotation=rotation,
           rotation_mode='anchor',
           ha=hjust,
           va=vjust,
           linespacing=linespacing)


def process_mtext_with_newlines(raw_text):
    """
    Обрабатывает MTEXT с сохранением переносов строк
    """
    if not raw_text:
        return ""
    
    # 1. Сохраняем переносы строк (\P -> \n)
    text = raw_text.replace('\\P', '\n')
    
    # 2. Удаляем форматирование {\fArial|b0|i1|c238|p34;текст}
    def extract_text(match):
        full_match = match.group(0)
        parts = full_match.split(';')
        if len(parts) > 1:
            text_part = parts[-1].rstrip('}')
            return text_part
        return ""
    
    text = re.sub(r'\{[^}]+\}', extract_text, text)
    
    # 3. Удаляем оставшиеся управляющие символы, но сохраняем \n
    text = re.sub(r'\\[A-Z][0-9]*;', '', text)
    text = text.replace('\\O', '')
    text = text.replace('\\L', '')
    text = text.replace('\\~', ' ')
    text = text.replace('\\ ', ' ')
    
    # 4. Убираем множественные пробелы, но сохраняем переносы строк
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = ' '.join(line.split())
        if line:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def extract_font_properties_fixed(raw_text):
    """Извлекает свойства шрифта из форматирования MTEXT"""
    font_weight = 'normal'
    font_style = 'normal'
    
    pattern = r'\\f[^|]+\|b([01])\|i([01])\|'
    match = re.search(pattern, raw_text)
    
    if match:
        bold = match.group(1) == '1'
        italic = match.group(2) == '1'
        
        if bold:
            font_weight = 'bold'
        if italic:
            font_style = 'italic'
    
    return font_weight, font_style


def get_text_alignment_fixed(entity):
    """Определяет выравнивание для обычного текста"""
    hjust = 'left'
    vjust = 'baseline'
    
    if hasattr(entity.dxf, 'halign'):
        halign = entity.dxf.halign
        if halign == 0:
            hjust = 'left'
        elif halign == 1:
            hjust = 'center'
        elif halign == 2:
            hjust = 'right'
        elif halign in [3, 4, 5]:
            hjust = 'center'
    
    if hasattr(entity.dxf, 'valign'):
        valign = entity.dxf.valign
        if valign == 0:
            vjust = 'baseline'
        elif valign == 1:
            vjust = 'bottom'
        elif valign == 2:
            vjust = 'center'
        elif valign == 3:
            vjust = 'top'
    
    return hjust, vjust


def get_mtext_alignment_fixed(attachment_point):
    """Определяет выравнивание для MTEXT"""
    alignment_map = {
        1: ('left', 'top'),
        2: ('center', 'top'),
        3: ('right', 'top'),
        4: ('left', 'middle'),
        5: ('center', 'middle'),
        6: ('right', 'middle'),
        7: ('left', 'bottom'),
        8: ('center', 'bottom'),
        9: ('right', 'bottom'),
    }
    
    return alignment_map.get(attachment_point, ('left', 'top'))


def save_figure_with_quality(fig, png_filepath, dpi, stats):
    """Сохраняет фигуру с высоким качеством"""
    print("💾 Сохранение PNG...")
    
    try:
        fig.savefig(
            png_filepath,
            format='png',
            dpi=dpi,
            bbox_inches='tight',
            pad_inches=0.05,
            facecolor='white',
            edgecolor='none',
            transparent=False
        )
        
        plt.close(fig)
        
        if os.path.exists(png_filepath):
            enhance_image_contrast(png_filepath)
            return png_filepath
        else:
            print("❌ PNG файл не создан")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        plt.close(fig)
        return None


def enhance_image_contrast(png_filepath):
    """Увеличивает контрастность изображения"""
    try:
        from PIL import Image, ImageEnhance
        
        img = Image.open(png_filepath)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Увеличиваем контрастность
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # Немного увеличиваем резкость
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        
        img.save(png_filepath, 'PNG')
        return True
        
    except:
        return False


def render_scaled_text_1(entity, ax, scale_factor):
    """Рисует обычный текст с правильным масштабом и стилем"""
    if not hasattr(entity.dxf, 'insert'):
        return
    
    x, y = entity.dxf.insert[0], entity.dxf.insert[1]
    text_content = getattr(entity.dxf, 'text', '').strip()
    
    if not text_content:
        return
    
    # Получаем высоту текста
    height_dxf = getattr(entity.dxf, 'height', 10)
    font_size = height_dxf * scale_factor
    font_size = max(font_size, 6)
    font_size = min(font_size, 72)
    
    # ✅ Получаем стиль шрифта (без doc, только из entity)
    font_weight = 'normal'
    font_style = 'normal'
    
    # Проверяем атрибуты текста
    if hasattr(entity.dxf, 'style'):
        style_name = entity.dxf.style
        if style_name:
            if 'Bold' in style_name or 'bold' in style_name:
                font_weight = 'bold'
            if 'Italic' in style_name or 'italic' in style_name:
                font_style = 'italic'
    
    # Поворот
    rotation = getattr(entity.dxf, 'rotation', 0)
    
    # Выравнивание
    hjust, vjust = get_text_alignment_fixed(entity)
    
    # Рисуем текст с учётом стиля
    ax.text(x, y, text_content,
           color='black',
           fontsize=font_size,
           fontweight=font_weight,      # ✅ жирный шрифт
           fontstyle=font_style,        # ✅ курсив
           rotation=rotation,
           rotation_mode='anchor',
           ha=hjust,
           va=vjust)






if __name__ == "__main__":
    # Основная функция
    result = dxf_to_jpg(
        dxf_filepath="/home/alex/TEST_SERVER/TEST_DXF/test.dxf",
        png_filepath="/home/alex/TEST_SERVER/TEST_DXF/test.png",
        dpi=200
    )