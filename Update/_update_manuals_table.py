import os
import sqlite3
from time import sleep
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# os.environ['HTTP_PROXY'] = 'http://1.1.1.40:3128'
# os.environ['HTTPS_PROXY'] = 'http://1.1.1.40:3128'


def update_manual_incompatibilities(sheet_url, db_name, batch_size=1000):
    """
    Обновляет таблицу Manual_incomp из Google Sheets
    Колонки: A-Модель, B-свойство1, C-характеристика1, D-свойство2, E-характеристика2, F-разрешение (1 или 0)
    """
    try:
        client = authorize_gspread()
        wks = client.open_by_url(sheet_url).worksheet("К выгрузке")

        # Получаем все данные
        print("📥 Загрузка данных из Google Sheets...")
        all_data = wks.get_all_values()
        
        if not all_data or len(all_data) <= 1:
            print("❌ Нет данных для обработки")
            return False
            
        total_rows = len(all_data)
        print(f"📊 Всего строк в таблице: {total_rows}")
        print(f"📋 Заголовки: {all_data[0]}")  # Показываем заголовки для проверки

        processed_count = 0
        error_count = 0
        
        with sqlite3.connect(db_name, timeout=10) as conn:
            cursor = conn.cursor()
            
            # Создаем таблицу если её нет (передаем db_name, а не conn)
            create_manual_incomp_table(db_name)
            
            for i in range(1, total_rows):  # Пропускаем заголовок (строка 0)
                row = all_data[i]
                
                # Пропускаем пустые строки
                if not row or len(row) < 6:
                    continue
                
                # Извлекаем данные по колонкам (исправляем индексы согласно вашим заголовкам)
                model_name = row[0].strip() if len(row) > 0 else ""
                prop1_name = row[1].strip() if len(row) > 1 else ""
                value1 = row[2].strip() if len(row) > 2 else ""
                prop2_name = row[3].strip() if len(row) > 3 else ""
                value2 = row[4].strip() if len(row) > 4 else ""
                resolution_str = row[5].strip() if len(row) > 5 else "0"
                
                # Проверяем обязательные поля
                if not all([model_name, prop1_name, value1, prop2_name, value2]):
                    print(f"⚠️  Строка {i+1}: пропущена - не заполнены обязательные поля")
                    continue
                
                # Преобразуем разрешение в число (более гибкая проверка)
                resolution = 0
                if resolution_str in ["1", "да", "yes", "true", "разрешено", "разрешить"]:
                    resolution = 1
                elif resolution_str in ["0", "нет", "no", "false", "запрещено", "запретить"]:
                    resolution = 0
                else:
                    # Если значение непонятное, считаем несовместимым (0)
                    resolution = 0
                    print(f"⚠️  Строка {i+1}: непонятное значение разрешения '{resolution_str}', установлено 0")
                
                try:
                    add_manual_incompatibility_record(
                        conn=conn,
                        cursor=cursor,
                        model_name=model_name,
                        prop1_name=prop1_name,
                        value1=value1,
                        prop2_name=prop2_name,
                        value2=value2,
                        resolution=resolution
                    )
                    processed_count += 1
                    
                    # Выводим прогресс каждые 100 строк
                    if processed_count % 100 == 0:
                        print(f"⏳ Обработано: {processed_count} строк")
                    
                except Exception as e:
                    error_count += 1
                    print(f"❌ Ошибка в строке {i+1}: {e}")
                    print(f"   Данные: {model_name} | {prop1_name}={value1} | {prop2_name}={value2} | разрешение={resolution}")

                # Фиксируем изменения пачками
                if processed_count % batch_size == 0:
                    conn.commit()
                    print(f"💾 Сохранение базы... Обработано: {processed_count} строк")
                    #sleep(1)  # Задержка для API

            # Финальное сохранение
            conn.commit()
            
        print(f"\n✅ Импорт завершён!")
        print(f"📈 Успешно обработано: {processed_count}")
        print(f"❌ Ошибок: {error_count}")
        print(f"📊 Эффективность: {(processed_count/(processed_count + error_count))*100:.1f}%")
        
        return True

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_manual_incomp_table(db_file):
    """
    Создает таблицу Manual_incomp если её нет
    """
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Manual_incomp (
            manual_id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER,
            model_name TEXT,
            property1_id INTEGER,
            property1_name TEXT,
            value1 TEXT,
            property2_id INTEGER,
            property2_name TEXT,
            value2 TEXT,
            resolution INTEGER NOT NULL DEFAULT 0,  -- 0 = несовместимо, 1 = разрешено
            comment TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (model_id) REFERENCES models (model_id),
            FOREIGN KEY (property1_id) REFERENCES properties (property_id),
            FOREIGN KEY (property2_id) REFERENCES properties (property_id)
        )
        """)
        
        # Индекс для быстрого поиска
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_manual_incomp_search 
        ON Manual_incomp (model_id, property1_id, value1, property2_id, value2)
        """)
        
        conn.commit()
        print("✅ Таблица Manual_incomp проверена/создана")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблицы: {e}")
    finally:
        conn.close()


def add_manual_incompatibility_record(conn, cursor, model_name, prop1_name, value1, 
                                     prop2_name, value2, resolution=0, comment=""):
    """
    Добавляет или обновляет запись в Manual_incomp
    """
    # Получаем ID модели и свойств
    cursor.execute("SELECT model_id FROM models WHERE model_name = ?", (model_name,))
    model_row = cursor.fetchone()
    if not model_row:
        raise ValueError(f"Модель '{model_name}' не найдена в базе")
    model_id = model_row[0]
    
    cursor.execute("SELECT property_id FROM properties WHERE property_name = ?", (prop1_name,))
    prop1_row = cursor.fetchone()
    if not prop1_row:
        raise ValueError(f"Свойство '{prop1_name}' не найдено в базе")
    prop1_id = prop1_row[0]
    
    cursor.execute("SELECT property_id FROM properties WHERE property_name = ?", (prop2_name,))
    prop2_row = cursor.fetchone()
    if not prop2_row:
        raise ValueError(f"Свойство '{prop2_name}' не найдено в базе")
    prop2_id = prop2_row[0]
    
    # Проверяем, существует ли уже такая запись
    cursor.execute("""
    SELECT manual_id FROM Manual_incomp 
    WHERE model_id = ? 
      AND property1_id = ? AND value1 = ?
      AND property2_id = ? AND value2 = ?
    """, (model_id, prop1_id, value1, prop2_id, value2))
    
    existing_record = cursor.fetchone()
    
    if existing_record:
        # Обновляем существующую запись
        cursor.execute("""
        UPDATE Manual_incomp 
        SET resolution = ?, comment = ?, updated_date = CURRENT_TIMESTAMP
        WHERE manual_id = ?
        """, (resolution, comment, existing_record[0]))
        # print(f"   🔄 Обновлена запись: {model_name} | {prop1_name}={value1} | {prop2_name}={value2}")
    else:
        # Добавляем новую запись
        cursor.execute("""
        INSERT INTO Manual_incomp 
        (model_id, model_name, property1_id, property1_name, value1, 
         property2_id, property2_name, value2, resolution, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (model_id, model_name, prop1_id, prop1_name, value1, 
              prop2_id, prop2_name, value2, resolution, comment))
        # print(f"   ✅ Добавлена запись: {model_name} | {prop1_name}={value1} | {prop2_name}={value2}")




def authorize_gspread():
    print("Starting authorized client...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    path_to_file = str(os.path.dirname(os.path.abspath(__file__))) + '/credentials.json'
    creds = ServiceAccountCredentials.from_json_keyfile_name(path_to_file, scope) # type: ignore
    client = gspread.authorize(creds) # type: ignore
    print("Connect succesful")
    return client

if __name__=='__main__':
    db_file='/home/alex/temp/doors1.db'
    google_url = "https://docs.google.com/spreadsheets/d/1aF6ZJNr47jAI1Gjt-EGOU8Se-kYNs9F-4KNQ_UQJG4k/edit?gid=906665945#gid=906665945"
    update_manual_incompatibilities(google_url, db_file)