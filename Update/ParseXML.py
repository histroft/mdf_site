import sqlite3
import xml.etree.ElementTree as ET


def parse_xml_and_update_db(db_path, xml_file_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    # Словари для кэширования
    properties_cache = {}
    options_cache = {}

    # 1. Получаем список моделей дверей с #777
    models_to_process = set()
    for nom in root.findall('.//Номенклатура'):
        model_name = nom.get('Модель')
        for var in nom.findall('ВариантИсполнения'):
            unique_comb = var.get('УникальноеСочетание', '')
            if '#777' in unique_comb:
                models_to_process.add(model_name)
                break
    models_to_process.add('TAU LT МP')
    models_to_process.add('TAU LT PP')
    models_to_process.add('TAU PRO PP')
    models_to_process.add('TAU PRO MP')
    models_to_process.add('DELTA LT PP')
    models_to_process.add('DELTA LT MP')
    models_to_process.add('DELTA MP FDL-EI 30')
    models_to_process.add('DELTA PP FDL-EI 30')
    models_to_process.add('DELTA MP FDL-EI 60')
    models_to_process.add('DELTA PP FDL-EI 60')
    models_to_process.add('ALFA LT PP')
    models_to_process.add('DIAMOND FS')
    models_to_process.add('SNEGIR HOME')
    #models_to_process.add('STARTER IO')

    
    
    

    # 2. Обрабатываем модели и их варианты
    for model_name in models_to_process:
        # Добавляем модель в БД
        cursor.execute('INSERT OR IGNORE INTO models (model_name) VALUES (?)', (model_name,))
        model_id = cursor.lastrowid or cursor.execute('SELECT model_id FROM models WHERE model_name = ?',
                                                      (model_name,)).fetchone()[0]
        # Получаем все варианты для этой модели
        for nom in root.findall(f'.//Номенклатура[@Модель="{model_name}"]'):
            for var in nom.findall('ВариантИсполнения'):
                unique_comb = var.get('УникальноеСочетание', '')
                print(model_name, unique_comb)
                # Добавляем вариант
                cursor.execute('''
                INSERT OR IGNORE INTO variants (model_id, unique_combination)
                VALUES (?, ?)
                ''', (model_id, unique_comb))
                variant_id = cursor.lastrowid or cursor.execute('''
                    SELECT variant_id FROM variants WHERE unique_combination = ?
                ''', (unique_comb,)).fetchone()[0]

                # Обрабатываем характеристики
                for char in var.findall('Характеристика'):
                    prop_name = char.get('Свойство')

                    # Добавляем свойство в кэш/БД
                    if prop_name not in properties_cache:
                        cursor.execute('''
                        INSERT OR IGNORE INTO properties (property_name) VALUES (?)
                        ''', (prop_name,))
                        prop_id = cursor.lastrowid or cursor.execute('''
                            SELECT property_id FROM properties WHERE property_name = ?
                        ''', (prop_name,)).fetchone()[0]
                        properties_cache[prop_name] = prop_id
                    prop_id = properties_cache[prop_name]

                    # Добавляем значения характеристик
                    for value in char.findall('Значение'):
                        val = value.text.strip() if value.text else ''
                        if val:
                            cursor.execute('''
                            INSERT OR IGNORE INTO characteristics 
                            (property_id, variant_id, value) VALUES (?, ?, ?)
                            ''', (prop_id, variant_id, val))

        # 3. Добавляем дополнительные опции для моделей с #777
        for nom in root.findall(f'.//Номенклатура[@Модель="{model_name}"]'):
            for var in nom.findall('ВариантИсполнения'):
                if '#777' in var.get('УникальноеСочетание', ''):
                    for opt in var.findall('.//ДополнительныеОпции/КодОпции'):
                        opt_code = opt.text.strip() if opt.text else ''
                        if opt_code:
                            # Находим описание опции
                            opt_name = ""
                            for o in root.findall(f'.//ДопОпция[@КодОпции="{opt_code}"]'):
                                opt_name = o.get('НаименованиеОпции', '')
                                break

                            if opt_code not in options_cache:
                                cursor.execute('''
                                INSERT OR IGNORE INTO options (option_code, option_name)
                                VALUES (?, ?)
                                ''', (opt_code, opt_name))
                                opt_id = cursor.lastrowid or cursor.execute('''
                                    SELECT option_id FROM options WHERE option_code = ?
                                ''', (opt_code,)).fetchone()[0]
                                options_cache[opt_code] = opt_id

                            # Связываем опцию с моделью
                            cursor.execute('''
                            INSERT OR IGNORE INTO model_options (model_id, option_id)
                            VALUES (?, ?)
                            ''', (model_id, options_cache[opt_code]))

    conn.commit()


if __name__ == '__main__':
    from config import Config
    db_name = Config.DATABASE
    xml_path = Config.XML
    parse_xml_and_update_db(db_name, xml_path)
