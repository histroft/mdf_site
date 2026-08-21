import sqlite3


def clear_table(DB_FILE):
    """
    Очищает указанную таблицу в базе данных.

    :param table_name: название таблицы, которую нужно очистить
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    tables_to_clear = [
        'incompatibilities',
        'model_options',
        'characteristics',
        'options',
        'variants',
        'properties',
        'models'
    ]

    print("Очистка базы данных...")
    for table in tables_to_clear:
        try:
            cursor.execute(f'DELETE FROM {table}')
            print(f"Таблица {table} очищена")
        except sqlite3.Error as e:
            print(f"Ошибка при очистке таблицы {table}: {e}")

    conn.commit()
