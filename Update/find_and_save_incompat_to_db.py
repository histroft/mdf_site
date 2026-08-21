import sqlite3
import os
import csv
from datetime import datetime
from itertools import product
from time import sleep
from find_all_models_IDEAl import find_global_incompatibilities
import gspread
from oauth2client.service_account import ServiceAccountCredentials

os.environ['HTTP_PROXY'] = 'http://1.1.1.40:3128'
os.environ['HTTPS_PROXY'] = 'http://1.1.1.40:3128'


def authorize_gspread():
    print("Starting authorized client...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    path_to_file = str(os.path.dirname(os.path.abspath(__file__))) + '/credentials.json'
    creds = ServiceAccountCredentials.from_json_keyfile_name(path_to_file, scope) # type: ignore
    client = gspread.authorize(creds) # type: ignore
    print("Connect succesful")
    return client


def get_property_id(cur, property_name):
    """
    Получает ID свойства по его названию из базы данных.
    
    Args:
        cur: Курсор базы данных
        property_name (str): Название свойства
        
    Returns:
        int or None: ID свойства или None если не найдено
    """
    try:
        cur.execute("SELECT id FROM properties WHERE name = ?", (property_name,))
        result = cur.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Ошибка при поиске свойства '{property_name}': {e}")
        return None


def find_and_save_global_incompatibilities_non_models(db_file):
    """
    Сначала создаем CSV файл, так как у него получился идеальный алгоритм. 
    Затем из получившегося CSV загружаем данные в базу.
    """
    print("=== ПОИСК И СОХРАНЕНИЕ АВТОМАТИЧЕСКИХ НЕСОВМЕСТИМОСТЕЙ ===")
    
    scv_name = "/home/alex/temp/incompat_for_bd.csv"
    print(f'Создаем файл CSV: {scv_name}')
    find_global_incompatibilities(db_file, scv_name)
    
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    print(f"📥 Чтение данных из CSV: {scv_name}")
    incompatibility_pairs = []
    
    with open(scv_name, 'r', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        
        try:
            headers = next(reader)
            print(f"📋 Заголовки CSV: {headers}")
        except StopIteration:
            print("ℹ️  CSV файл не содержит заголовков")
        
        for i, row in enumerate(reader, 1):
            if len(row) >= 4:
                property1_name = row[0].strip()  # Название первого свойства
                value1 = row[1].strip()
                property2_name = row[2].strip()  # Название второго свойства
                value2 = row[3].strip()
                
                if property1_name and value1 and property2_name and value2:
                    # ПРЕОБРАЗУЕМ названия свойств в ID
                    property1_id = get_property_id(cur, property1_name)
                    property2_id = get_property_id(cur, property2_name)
                    
                    if property1_id and property2_id:
                        incompatibility_pairs.append((property1_id, value1, property2_id, value2))
                    else:
                        print(f"⚠️  Строка {i}: не найдены ID для свойств '{property1_name}' или '{property2_name}'")
                else:
                    print(f"⚠️  Строка {i}: пропущена - не все поля заполнены")
    
    print(f"✅ Прочитано пар из CSV: {len(incompatibility_pairs)}")
    
    if not incompatibility_pairs:
        print("❌ Нет данных для добавления в базу")
        return 0
    
    # Добавляем данные в таблицу
    print("💾 Добавление данных в базу...")
    added_count = 0
    
    for property1_id, value1, property2_id, value2 in incompatibility_pairs:
        try:
            cur.execute("""
            INSERT INTO incompatibilities_non_models 
            (property1_id, value1, property2_id, value2)
            VALUES (?, ?, ?, ?)
            """, (property1_id, value1, property2_id, value2))
            
            added_count += 1
                
        except Exception as e:
            print(f"❌ Ошибка при добавлении property1_id={property1_id}={value1} + property2_id={property2_id}={value2}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Успешно добавлено записей: {added_count}")
    
    
    
def find_and_save_global_incompatibilities_models(db_name, sheet_url ,batch_size=1000):
    # Эта функция должна сгрузить все данные из Гугл таблицы CSV в Базу Данных incompatibilities
    """
    Обновляет таблицу Manual_incomp из Google Sheets
    Колонки: A-Модель, B-свойство1, C-характеристика1, D-свойство2, E-характеристика2, F-разрешение (1 или 0)
    """
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
                
                # # Пропускаем пустые строки
                # if not row or len(row) < 6:
                #     continue
    
                
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



  
if __name__=='__main__':
    db_file='/home/alex/temp/doors.db'
    sheet_url = "https://docs.google.com/spreadsheets/d/1aF6ZJNr47jAI1Gjt-EGOU8Se-kYNs9F-4KNQ_UQJG4k/edit?gid=906665945#gid=906665945"
    find_and_save_global_incompatibilities_non_models(db_file)
      
    
    
    

    
    
    
    
    
    
    
    
    
