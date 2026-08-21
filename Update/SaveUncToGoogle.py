




import sqlite3
import gspread
from time import sleep
from oauth2client.service_account import ServiceAccountCredentials
import os


os.environ['HTTP_PROXY'] = 'http://1.1.1.40:3128'
os.environ['HTTPS_PROXY'] = 'http://1.1.1.40:3128'


def authorize_gspread():
    print("Starting authorized client...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    path_to_file = str(os.path.dirname(os.path.abspath(__file__))) + '/credentials.json'
    creds = ServiceAccountCredentials.from_json_keyfile_name(path_to_file, scope)
    client = gspread.authorize(creds)
    print("Connect succesful")
    return client


def find_specific_incompatibilities_to_gsheet(db_file, spreadsheet_url, worksheet_name="CSV"):
    """
    Находит несовместимости для всех моделей и сохраняет в Google Таблицу.
    Проверяет пары характеристик в обе стороны.
    """
    # Авторизация в Google Sheets
    try:
        client = authorize_gspread()

        # Открываем таблицу по URL
        spreadsheet = client.open_by_url(spreadsheet_url)
        print(f"✅ Подключились к таблице по URL: {spreadsheet.title}")

        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols="10")

        # Очищаем весь лист полностью
        worksheet.clear()
        print(f"Лист '{worksheet_name}' полностью очищен")

        # Записываем заголовки в первую строку
        headers = ["Модель", "Характеристика 1", "Значение 1", "Характеристика 2", "Значение 2"]
        worksheet.update('A1', [headers])
        print("Заголовки записаны в первую строку")

    except Exception as e:
        print(f"Ошибка при работе с Google Таблицей: {e}")
        return

    # Подключаемся к базе данных
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # Получаем ID свойств
    cur.execute("SELECT property_id, property_name FROM properties")
    property_ids = {prop_name: prop_id for prop_id, prop_name in cur.fetchall()}
    print(f"Найдены свойства: {list(property_ids.keys())}")

    # Извлекаем все модели (кроме содержащих #777)
    cur.execute("""
    SELECT model_id, model_name 
    FROM models
    WHERE 
        model_name NOT LIKE '%#777%' AND
        model_name NOT LIKE '%.Комплект О3%' AND
        model_name NOT LIKE '%Панель%' AND
        model_name NOT LIKE '%Добор%' AND
        model_name NOT LIKE '%DIAMOND FS%' AND
        model_name NOT LIKE '%DELTA LT PP%' AND
        model_name NOT LIKE '%SNEGIR HOME%' AND
        model_name NOT LIKE '%ALFA LT PP%' AND
        model_name NOT LIKE '%DELTA LT MP%' AND
        model_name NOT LIKE '%DELTA LT PP%' AND
        model_name NOT LIKE '%DELTA MP FDL-EI 60%' AND
        model_name NOT LIKE '%DELTA MP FDL-EI 30%' AND
        model_name NOT LIKE '%DELTA PP FDL-EI 60%' AND
        model_name NOT LIKE '%DELTA PP FDL-EI 30%' AND
        model_name NOT LIKE '%TAU LT МP%' AND
        model_name NOT LIKE '%TAU LT PP%' AND
        model_name NOT LIKE '%TAU PRO PP%' AND
        model_name NOT LIKE '%TAU PRO MP%' AND
        model_name NOT LIKE '%Надставка Термо' AND
        
        
        model_name NOT LIKE '%TAU LT PP%' 
        
        
        
    """)
    models = cur.fetchall()
    print(f"Найдены модели: {[model[1] for model in models]}")

    # ДВУСТОРОННИЙ список пар для проверки
    bidirectional_pairs = [
        # Ширина ↔ все остальные
        ("01_Ширина", "04_Лицо (цвет)"),
        ("01_Ширина", "05_Лицо (рисунок)"),
        ("01_Ширина", "06_Внутр. отделка (цвет)"),
        ("01_Ширина", "07_Внутр. отделка (рисунок)"),

        # Высота ↔ все остальные
        ("02_Высота", "04_Лицо (цвет)"),
        ("02_Высота", "05_Лицо (рисунок)"),
        ("02_Высота", "06_Внутр. отделка (цвет)"),
        ("02_Высота", "07_Внутр. отделка (рисунок)"),

        # Лицо (цвет) ↔ остальные
        ("04_Лицо (цвет)", "05_Лицо (рисунок)"),

        # Внутр. отделка (цвет) ↔ остальные
        ("06_Внутр. отделка (цвет)", "07_Внутр. отделка (рисунок)"),
    ]

    # Подготавливаем данные для записи
    data_to_write = []
    incompatibility_count = 0
    checked_combinations = set()  # Для избежания дубликатов

    for model_id, model_name in models:
        print(f"\n🔍 Обрабатываем модель: {model_name}")

        for prop1_name, prop2_name in bidirectional_pairs:
            prop1_id = property_ids.get(prop1_name)
            prop2_id = property_ids.get(prop2_name)

            if not prop1_id or not prop2_id:
                print(f"⏭️ Пропускаем: {prop1_name} или {prop2_name} не найдены")
                continue

            # Создаем уникальный ключ для комбинации свойств и модели
            combo_key = f"{model_id}_{min(prop1_id, prop2_id)}_{max(prop1_id, prop2_id)}"
            if combo_key in checked_combinations:
                continue
            checked_combinations.add(combo_key)

            print(f"   Проверяем пару: {prop1_name} ↔ {prop2_name}")

            # Получаем ВСЕ значения для обеих характеристик
            cur.execute("""
            SELECT DISTINCT c.value
            FROM characteristics c
            JOIN variants v ON c.variant_id = v.variant_id
            WHERE v.model_id = ? 
              AND c.property_id = ?
              AND v.unique_combination NOT LIKE '%#777%'
            ORDER BY c.value
            """, (model_id, prop1_id))
            values1 = [row[0] for row in cur.fetchall()]

            cur.execute("""
            SELECT DISTINCT c.value
            FROM characteristics c
            JOIN variants v ON c.variant_id = v.variant_id
            WHERE v.model_id = ? 
              AND c.property_id = ?
              AND v.unique_combination NOT LIKE '%#777%'
            ORDER BY c.value
            """, (model_id, prop2_id))
            values2 = [row[0] for row in cur.fetchall()]

            if not values1 or not values2:
                print(f"   ⏭️ Пропускаем - нет значений для одной из характеристик")
                continue

            print(f"   {prop1_name}: {len(values1)} значений")
            print(f"   {prop2_name}: {len(values2)} значений")

            # Проверяем ВСЕ возможные комбинации
            for value1 in values1:
                for value2 in values2:
                    # Проверяем существование комбинации в БД
                    cur.execute("""
                    SELECT 1 FROM variants v
                    JOIN characteristics c1 ON v.variant_id = c1.variant_id
                    JOIN characteristics c2 ON v.variant_id = c2.variant_id
                    WHERE v.model_id = ?
                      AND v.unique_combination NOT LIKE '%#777%'
                      AND (
                        (c1.property_id = ? AND c1.value = ? AND c2.property_id = ? AND c2.value = ?)
                        OR
                        (c1.property_id = ? AND c1.value = ? AND c2.property_id = ? AND c2.value = ?)
                      )
                    LIMIT 1;
                    """, (model_id, prop1_id, value1, prop2_id, value2, prop2_id, value2, prop1_id, value1))

                    if not cur.fetchone():
                        # Записываем несовместимость в обоих направлениях
                        data_to_write.append([
                            model_name,
                            prop1_name,
                            str(value1),
                            prop2_name,
                            str(value2)
                        ])
                        incompatibility_count += 1
                        print(f"   🚫 НЕСОВМЕСТИМОСТЬ: {prop1_name}={value1} ≠ {prop2_name}={value2}")

    # Закрываем соединение с базой
    conn.close()

    # Записываем данные в Google Таблицу
    try:
        if incompatibility_count > 0:
            print(f"\n📊 Найдено несовместимостей: {incompatibility_count}")
            print(f"💾 Записываем данные в Google Таблицу...")

            # Записываем данные пачками
            batch_size = 500
            for i in range(0, len(data_to_write), batch_size):
                batch = data_to_write[i:i + batch_size]
                start_row = i + 2
                end_row = start_row + len(batch) - 1
                range_name = f"A{start_row}:E{end_row}"

                worksheet.update(range_name, batch)
                print(f"   Записано {min(i + batch_size, len(data_to_write))}/{len(data_to_write)} строк")

                if i + batch_size < len(data_to_write):
                    sleep(1)  # Пауза между батчами

            # Форматирование
            try:
                worksheet.format('A1:E1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
                    'horizontalAlignment': 'CENTER'
                })
                worksheet.columns_auto_resize(0, 4)
                print("✅ Форматирование применено")
            except Exception as format_error:
                print(f"⚠️ Ошибка форматирования: {format_error}")

        else:
            worksheet.update('A2', [["Несовместимости не найдены"]])
            print("ℹ️ Несовместимости не найдены")

    except Exception as e:
        print(f"❌ Ошибка при записи в Google Таблицу: {e}")


# Пример использования


# Использование
if __name__ == "__main__":
    DB_FILE = '/home/alex/DB/doors.db'
    sheet_url="https://docs.google.com/spreadsheets/d/1aF6ZJNr47jAI1Gjt-EGOU8Se-kYNs9F-4KNQ_UQJG4k/edit?gid=246894749#gid=246894749"
    find_specific_incompatibilities_to_gsheet(DB_FILE, sheet_url)