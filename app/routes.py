
import traceback
import os
from flask import Blueprint, jsonify, render_template, redirect, request, url_for, current_app, send_file, send_from_directory
from flask_login import current_user, login_required
from config import Config

# Импорты из модулей проекта
from auth.decorators import auth_required, get_username_safe
from auth.users import authenticate_user, generate_token, add_user

# Импорты для работы с моделями
from models.get_models_list import GetListModel
from models.characteristics import get_model_characteristics
from models.get_model_options import get_model_options

# Импорты для работы с заказами
from make_order.MakeDoorPDF import MakeDoorDXF
from make_order.MakePanelPDF import MakePanelDXF
from make_order.database import find_order

# Импорты для валидации
from validation.check_backlight import backlight
from validation.main import is_possible_make_detailed
#from validation.FindMissChar_temp import find_missing_characteristics


from config import Config
from database.statistic import add_record


# Импорты для экономической части
from Economical.calculator import calculate_price, calculate_head_price


# Импорты для базы данных
from database.statistic import add_record

main_bp = Blueprint('main', __name__)

def get_db_path():
    """Возвращает путь к базе данных моделей"""
    return Config.DATABASE

def get_price_db_path():
    """Возвращает путь к базе данных цен"""
    return Config.NEW_PATH_TO_PRICE_DB

def get_orders_dir():
    """Возвращает директорию для заказов"""
    return Config.ORDERS_DIR

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    db_path = get_db_path()
    list_models = GetListModel(db_path)
    # Динамически получаем списки текстур для стен и полов
    from app.door3d.scene_catalog import get_dynamic_scene_textures
    scene_walls, scene_floors = get_dynamic_scene_textures()
    
    return render_template('dashboard.html', 
                         list_models=list_models,
                         scene_walls=scene_walls,
                         scene_floors=scene_floors,
                         username=current_user.username)


# Эндпоинт для получения полей подсветки BACKLIGHT
@main_bp.route('/api/backlight', methods=['POST'])
@login_required
def backlight_route():
    """Возвращает поля, не соответствующие стандартным исполнениям"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        model = data.get('model')
        characteristics = data.get('characteristic', {})
        
        if not model:
            return jsonify({'error': 'Не указана модель'}), 400
        
        db_path = get_db_path()
        
        # Импортируем функцию backlight
        from validation.check_backlight import backlight
        
        # Получаем отсутствующие характеристики
        missing = backlight(db_path, model, characteristics)
        
        # missing - это словарь, где ключи - названия полей
        # {'04_Лицо (цвет)': {...}, '05_Лицо (рисунок)': {...}}
        
        return jsonify({
            'success': True,
            'problem_fields': list(missing.keys())  # список полей для подсветки
        })
        
    except Exception as e:
        print(f"❌ Ошибка в backlight: {e}")
        return jsonify({'error': str(e)}), 500


# ПОЛУЧАЕМ ХАРАКТЕРИСТИКИ И ОПЦИИ ДЛЯ МОДЕЛИ
@main_bp.route('/api/select-model', methods=['POST'])
@login_required
def api_select_model():
    try:
        data = request.get_json()
        selected_model = data.get('model')
        
        if not selected_model:
            return jsonify({
                'status': 'error',
                'message': 'Модель не указана'
            }), 400
        
        db_path = get_db_path()
        
        # Получаем характеристики
        list_chars = get_model_characteristics(db_path, selected_model)
        
        # Преобразуем список в словарь, если нужно
        if isinstance(list_chars, list):
            chars_dict = {}
            for char in list_chars:
                if isinstance(char, dict):
                    # Если это список объектов с id и options
                    char_name = char.get('name') or char.get('id')
                    char_options = char.get('options', [])
                    if char_name:
                        chars_dict[char_name] = char_options
                elif isinstance(char, (list, tuple)) and len(char) >= 2:
                    # Если это список [name, options]
                    chars_dict[char[0]] = char[1]
            list_chars = chars_dict
            print(f"Converted to dict with {len(list_chars)} items")
        
        # Получаем опции
        list_options = get_model_options(db_path, selected_model)
        
        return jsonify({
            'status': 'success',
            'message': f'Модель {selected_model} выбрана',
            'model': selected_model,
            'list_chars': list_chars,  # Теперь это словарь
            'list_options': list_options,
        })
        
    except Exception as e:
        print(f"❌ Ошибка в select-model: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@main_bp.route('/api/check-possibility', methods=['POST'])
@login_required
def check_possibility():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'Нет данных'}), 400
        
        model = data.get('model')
        if not model:
            return jsonify({'success': False, 'message': 'Не указана модель'}), 400
        
        db_file = get_db_path()
        mdf_db = Config.MDF_DB
        
        # Получаем результат проверки
        is_possible, message, problem_fields = is_possible_make_detailed(db_file, mdf_db, data)
        
        # Формируем ответ
        response_data = {
            'success': is_possible,
            'can_make': is_possible,
            'message': message,
            'problem_fields': problem_fields,
            'non_standard_fields': []
        }
        
        # Для отладки выводим в консоль сервера
        print(f"📤 Ответ API: success={is_possible}, message={message}, problem_fields={problem_fields}")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Ошибка в check_possibility: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'can_make': False,
            'message': f'Ошибка сервера: {str(e)}',
            'problem_fields': [],
            'non_standard_fields': []
        }), 500
     
     
     
   




       
# Эндпоинт для получения списка моделей для десктоп версии
@main_bp.route('/api/models', methods=['GET'])
@login_required
def get_models_list():
    """Возвращает список моделей"""
    try:
        db_path = get_db_path()
        models = GetListModel(db_path)
        
        # Скрываем ненужные модели
        models_to_hide = [
            'TAU LT МP', 'TAU LT PP', 'TAU PRO PP', 'TAU PRO MP',
            'DELTA LT PP', 'DELTA LT MP', 'SNEGIR HOME',
            'DELTA MP FDL-EI 30', 'DELTA PP FDL-EI 30',
            'DELTA MP FDL-EI 60', 'DELTA PP FDL-EI 60',
            'ALFA LT PP', 'DIAMOND FS'
        ]
        
        filtered = [m for m in models if m not in models_to_hide]
        
        return jsonify({'models': filtered})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



 
@main_bp.route('/api/calc-order', methods=['POST'])
@login_required
def api_calc_order():
    """Расчет стоимости заказа"""
    try:
        price_db_path = get_price_db_path()
        if not price_db_path or not os.path.exists(price_db_path):
            return jsonify({'success': False, 'message': 'База данных цен не найдена'}), 500
            
        data = request.get_json()
        
        if not data or 'data' not in data:
            return jsonify({'success': False, 'message': 'Нет данных для расчета'}), 400
        
        # ✅ Только один вызов - calculate_price уже включает надставку
        total_cost, info = calculate_price(price_db_path, data['data'])
        
        return jsonify({'success': True, 'cost': total_cost, 'info': info}), 200

    except Exception as e:
        print(f"❌ Server Error: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500
    

@main_bp.route('/api/make-order', methods=['POST'])
@login_required
def make_order():
    """Создание заказа"""
    try:
        price_db_path = get_price_db_path()
        orders_dir = get_orders_dir()
        db_path = get_db_path()

        if not all([price_db_path, orders_dir, db_path]):
            return jsonify({'success': False, 'message': 'Конфигурация сервера неполная'}), 500

        request_data = request.get_json()
        
        if not request_data or 'data' not in request_data:
            return jsonify({'success': False, 'message': 'Нет данных заказа'}), 400
        
        order_data = request_data['data']
        model = order_data.get('model')
        
        # Проверка возможности изготовления
        result = is_possible_make_detailed(db_path, model, order_data)
        
        # Обрабатываем результат
        if isinstance(result, dict):
            is_possible = result.get('success', False)
            problem_fields = result.get('problem_fields', [])
        elif isinstance(result, tuple):
            if len(result) >= 2:
                is_possible, problem_fields = result[0], result[1]
            else:
                is_possible = bool(result)
                problem_fields = []
        else:
            is_possible = bool(result)
            problem_fields = []
        
        if not is_possible:
            return jsonify({
                'success': False,
                'can_make': False,
                'message': 'Изготовление запрещено',
                'problem_fields': problem_fields
            }), 400
        
        # Добавляем менеджера
        order_data['manager'] = current_user.username
        
        # Расчет стоимости
        cost, info = calculate_price(price_db_path, order_data)
        order_data['cost'] = cost
        
        
        # Создание заказа
        if 'Панель' in order_data['model']:
            order= MakePanelDXF(order_data)
            contract_id = order.build_all() 
        else:
            order = MakeDoorDXF(order_data)
            contract_id = order.build_all()
        
        
        
        if not contract_id:
            return jsonify({'success': False, 'message': 'Не удалось создать контракт'}), 500

        # Запись в статистику
        add_record(
            statistic_db=Config.STATISTIC,  # путь к БД статистики
            data=order_data,                 # данные заказа
            is_possible=True,                # результат проверки (успешно)
            manager=current_user.username    # имя менеджера
            )
        
        pdf_path = os.path.join(orders_dir, f"{contract_id}_", "door_dxf_out.pdf")
        
        response_data = {
            'success': True,
            'can_make': True,
            'contract_id': contract_id,
            'pdf_url': f'/api/download-pdf/{contract_id}',
            'sketch_url': f'/api/get-sketch/{contract_id}',
            'info': info,
            'total_price': cost
        }
        
        if os.path.exists(pdf_path):
            return jsonify(response_data), 200
        else:
            response_data['message'] = 'Заказ создан, PDF готовится'
            return jsonify(response_data), 202

    except Exception as e:
        print(f"❌ Ошибка в make_order: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500
        

@main_bp.route('/api/download-pdf/<contract_id>', methods=['GET'])
@login_required
def download_pdf(contract_id):
    """Скачивание PDF заказа"""
    

    try:
        orders_dir = get_orders_dir()
        order_folder = f"{contract_id}" 
        pdf_path = os.path.join(orders_dir, order_folder, "main.pdf")
        
        print(f"🔍 Поиск PDF: {pdf_path}")
        
        if os.path.exists(pdf_path):
            return send_file(
                pdf_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f"order_{contract_id}.pdf"
            )
        else:
            # Альтернативный путь
            alt_pdf = os.path.join(orders_dir, order_folder, "main.pdf")
            if os.path.exists(alt_pdf):
                return send_file(alt_pdf, mimetype='application/pdf', as_attachment=True)
            
            return jsonify({'error': 'PDF не найден', 'path': pdf_path}), 404
            
    except Exception as e:
        print(f"Ошибка скачивания PDF: {e}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/get-sketch/<contract_id>', methods=['GET'])
@login_required
def get_sketch(contract_id):
    """Получение эскиза заказа"""
    try:
        orders_dir = get_orders_dir()
        order_folder = f"{contract_id}"  # без нижнего подчеркивания, как в get_png
        sketch_path = os.path.join(orders_dir, order_folder, 'main.png')
        
        print(f"🔍 Поиск эскиза: {sketch_path}")
        print(f"   Папка заказа: {order_folder}")
        print(f"   Файл существует: {os.path.exists(sketch_path)}")
        
        if os.path.exists(sketch_path):
            return send_file(sketch_path, mimetype='image/png')
        else:
            # Попробуем альтернативный путь (main.png)
            alt_path = os.path.join(orders_dir, order_folder, 'main.png')
            if os.path.exists(alt_path):
                return send_file(alt_path, mimetype='image/png')
            
            # Список файлов в папке для отладки
            folder_path = os.path.join(orders_dir, order_folder)
            if os.path.exists(folder_path):
                files = os.listdir(folder_path)
                print(f"   Файлы в папке: {files}")
            else:
                print(f"   Папка не существует: {folder_path}")
            
            #logger.error(f"Эскиз не найден для заказа {contract_id} в папке {order_folder}")
            return jsonify({'error': f"Эскиз не найден для заказа {contract_id}", 'path': folder_path}), 404
            
    except Exception as e:
        print(f"Ошибка получения эскиза: {e}")
        #logger.error(f"Error getting sketch: {e}")
        return jsonify({'error': f"Ошибка получения эскиза: {str(e)}"}), 500

@main_bp.route('/api/find-order', methods=['POST'])
@login_required
def find_order_route():
    """Поиск заказа по ID"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Нет данных запроса'}), 400
            
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'error': 'Не указан order_id'}), 400
        
        # Используем find_order из orders_new.database
        order = find_order(order_id)
        
        if not order:
            return jsonify({'error': 'Заказ не найден'}), 404
        
        # Проверяем, существует ли эскиз для этого заказа
        orders_dir = get_orders_dir()
        order_folder = os.path.join(orders_dir, str(order_id))
        sketch_path = os.path.join(order_folder, 'main.png')
        
        sketch_exists = os.path.exists(sketch_path)
        
        # Добавляем информацию об эскизе в ответ
        response_data = {
            'order': order,
            'sketch_exists': sketch_exists,
            'sketch_url': f'/api/get-sketch/{order_id}' if sketch_exists else None
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Ошибка поиска заказа: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== 3D-ГЕНЕРАТОР ДВЕРИ ====================

@main_bp.route('/api/generate-3d', methods=['POST'])
@login_required
def generate_3d_start():
    """Передаёт RENDER_NEW то же тело data, что используется для договора."""
    try:
        from app.door3d.runner import start_job

        request_data = request.get_json()
        if not request_data or 'data' not in request_data:
            return jsonify({'success': False, 'message': 'Нет данных заказа'}), 400

        job_id, unmapped = start_job(request_data)

        return jsonify({
            'success': True,
            'job_id': job_id,
            'unmapped': unmapped,
        }), 202

    except ValueError as e:
        print(f"Ошибка параметров 3D: {e}")
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        print(f"❌ Ошибка запуска 3D: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500


@main_bp.route('/api/generate-3d/status/<job_id>', methods=['GET'])
@login_required
def generate_3d_status(job_id):
    """Возвращает статус задачи генерации."""
    try:
        from app.door3d.runner import get_status
        return jsonify(get_status(job_id))
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@main_bp.route('/api/generate-3d/image/<job_id>/<side>', methods=['GET'])
@login_required
def generate_3d_image(job_id, side):
    """Отдаёт готовую картинку (side ∈ out|in)."""
    try:
        from app.door3d.runner import image_path
        path = image_path(job_id, side)
        if os.path.exists(path):
            return send_file(path, mimetype='image/png')
        return jsonify({'error': 'Изображение ещё не готово'}), 404
    except ValueError:
        return jsonify({'error': 'Задача не найдена'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/3d-preview/scene', methods=['GET'])
@login_required
def preview_scene_texture():
    """Отдаёт кешированную миниатюру разрешённой текстуры стены или пола."""
    try:
        from app.door3d.previews import resolve_scene_texture, thumbnail_path

        source = resolve_scene_texture(request.args.get('asset', ''))
        preview = thumbnail_path(source)
        return send_file(
            preview,
            mimetype='image/webp',
            conditional=True,
            max_age=0,
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        return jsonify({'error': str(e)}), 404


@main_bp.route('/api/3d-preview/finish', methods=['GET'])
@login_required
def preview_finish_texture():
    """Отдаёт миниатюру той же отделки, которую выберет RENDER_NEW."""
    try:
        from app.door3d.previews import resolve_finish_texture, thumbnail_path

        source = resolve_finish_texture(request.args.get('name', ''))
        preview = thumbnail_path(source)
        return send_file(
            preview,
            mimetype='image/webp',
            conditional=True,
            max_age=0,
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        return jsonify({'error': str(e)}), 404


@main_bp.route('/api/3d-preview/design', methods=['GET'])
@login_required
def preview_door_design():
    """Отдаёт миниатюру рисунка для селектора отделки."""
    try:
        from app.door3d.previews import resolve_door_design_preview, thumbnail_path

        source = resolve_door_design_preview(request.args.get('name', ''))
        preview = thumbnail_path(source)
        return send_file(
            preview,
            mimetype='image/webp',
            conditional=True,
            max_age=0,
        )
    except (ValueError, FileNotFoundError, OSError) as e:
        return jsonify({'error': str(e)}), 404
