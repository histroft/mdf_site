
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sqlite3

from CreateDB import create_database

from ParseXML import parse_xml_and_update_db
from _update_manuals_table import update_manual_incompatibilities
from _update_non_models_table import find_and_save_global_incompatibilities_non_models

#

os.environ['HTTP_PROXY'] = 'http://1.1.1.40:3128'
os.environ['HTTPS_PROXY'] = 'http://1.1.1.40:3128'



def find_and_save_global_incompatibilities_models(db_name, sheet_url ,batch_size=1000):
    # Эта функция должна сгрузить все данные из Гугл таблицы CSV в Базу Данных incompatibilities
    """
    Обновляет таблицу Manual_incomp из Google Sheets
    Колонки: A-Модель, B-свойство1, C-характеристика1, D-свойство2, E-характеристика2, F-разрешение (1 или 0)
    """
    
    list_models_non_rec=['DIAMOND FS','DELTA LT PP','SNEGIR HOME', 'ALFA LT PP','DELTA LT MP','TAU LT PP']
    try:
        client = authorize_gspread()
        wks = client.open_by_url(sheet_url).worksheet("CSV")

        # Получаем все данные
        print("📥 Загрузка данных из Google Sheets...")
        all_data = wks.get_all_values()
        
        if not all_data or len(all_data) <= 1:
            print("❌ Нет данных для обработки")
            return False
            
        total_rows = len(all_data)
 

        processed_count = 0
        error_count = 0
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            for i in range(1, total_rows):  # Пропускаем заголовок (строка 0)
                row = all_data[i]
                             
                # Извлекаем данные по колонкам (исправляем индексы согласно вашим заголовкам)
                model_name = row[0].strip() if len(row) > 0 else ""
                prop1_name = row[1].strip() if len(row) > 1 else ""
                value1 = row[2].strip() if len(row) > 2 else ""
                prop2_name = row[3].strip() if len(row) > 3 else ""
                value2 = row[4].strip() if len(row) > 4 else ""
                print(model_name, prop1_name, value1, prop2_name, value2)
                # Проверяем обязательные поля
                if not all([model_name, prop1_name, value1, prop2_name, value2]):
                    print(f"⚠️  Строка {i+1}: пропущена - не заполнены обязательные поля")
                    continue
                
                

                try:
                    add_manual_incompatibility_record(
                        conn=conn,
                        cursor=cursor,
                        model_name=model_name,
                        prop1_name=prop1_name,
                        value1=value1,
                        prop2_name=prop2_name,
                        value2=value2
                    )
                    processed_count += 1
                    
                    # Выводим прогресс каждые 100 строк
                    if processed_count % 100 == 0:
                        print(f"⏳ Обработано: {processed_count} строк")
                    
                except Exception as e:
                    error_count += 1
                    print(f"❌ Ошибка в строке {i+1}: {e}")
                    print(f"   Данные: {model_name} | {prop1_name}={value1} | {prop2_name}={value2}")

                # Фиксируем изменения пачками
                if processed_count % batch_size == 0:
                    conn.commit()
                    print(f"💾 Сохранение базы... Обработано: {processed_count} строк")
                    

            # Финальное сохранение
            conn.commit()
 
        return True

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    
    
def authorize_gspread():
    print("Starting authorized client...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    path_to_file = str(os.path.dirname(os.path.abspath(__file__))) + '/credentials.json'
    creds = ServiceAccountCredentials.from_json_keyfile_name(path_to_file, scope) # type: ignore
    client = gspread.authorize(creds) # type: ignore
    print("Connect succesful")
    return client


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
    SELECT incompatibility_id FROM incompatibilities 
    WHERE model_id = ? 
      AND property1_id = ? AND value1 = ?
      AND property2_id = ? AND value2 = ?
    """, (model_id, prop1_id, value1, prop2_id, value2))
    
    existing_record = cursor.fetchone()
    
    if existing_record:
       pass
    else:
        # Добавляем новую запись
        cursor.execute("""
        INSERT INTO incompatibilities 
        (model_id, property1_id,  value1, 
         property2_id,  value2)
        VALUES (?, ?, ?, ?, ?)
        """, (model_id,  prop1_id,  value1, 
              prop2_id,  value2))
        # print(f"   ✅ Добавлена запись: {model_name} | {prop1_name}={value1} | {prop2_name}={value2}")


if __name__ == "__main__":
    DB_FILE = '/home/alex/DB/doors.db'
    