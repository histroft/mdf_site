import sqlite3
from tabulate import tabulate# pip install tabulate

def get_table_structure(db_path: str, table_name: str):
    """
    Получает полную структуру таблицы
    
    Args:
        db_path: путь к базе данных
        table_name: имя таблицы
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        print(f"\n{'='*60}")
        print(f"СТРУКТУРА ТАБЛИЦЫ: {table_name}")
        print(f"{'='*60}")
        
        # 1. Получить SQL создания таблицы
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        create_sql = cursor.fetchone()
        if create_sql:
            print("\nSQL создания таблицы:")
            print("-" * 40)
            print(create_sql[0])
        
        # 2. Получить информацию о столбцах
        print("\nСтолбцы таблицы:")
        print("-" * 40)
        
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        columns = cursor.fetchall()
        
        # Форматируем вывод
        headers = ["ID", "Имя", "Тип", "NOT NULL", "Знач. по умол.", "PK"]
        rows = []
        for col in columns:
            rows.append([
                col[0],  # cid
                col[1],  # name
                col[2],  # type
                "✓" if col[3] else "",  # notnull
                col[4] if col[4] else "",  # dflt_value
                "✓" if col[5] else ""  # pk
            ])
        
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        
        # 3. Получить информацию об индексах
        print("\nИндексы таблицы:")
        print("-" * 40)
        
        cursor.execute(f"PRAGMA index_list('{table_name}')")
        indexes = cursor.fetchall()
        
        if indexes:
            for idx in indexes:
                idx_name = idx[1]
                idx_unique = "UNIQUE" if idx[2] else "NON-UNIQUE"
                idx_origin = idx[3]
                idx_partial = idx[4]
                
                print(f"\nИндекс: {idx_name}")
                print(f"  Тип: {idx_unique}")
                print(f"  Столбцы:")
                
                # Получить столбцы индекса
                cursor.execute(f"PRAGMA index_info('{idx_name}')")
                idx_columns = cursor.fetchall()
                
                for idx_col in idx_columns:
                    print(f"    - {idx_col[2]}")
        else:
            print("Индексы не найдены")
        
        # 4. Получить статистику таблицы
        print("\nСтатистика:")
        print("-" * 40)
        
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        print(f"Количество строк: {row_count:,}")
        
        # Примерный размер таблицы
        cursor.execute(f"SELECT SUM(pgsize) FROM dbstat WHERE name='{table_name}'")
        size_result = cursor.fetchone()
        if size_result and size_result[0]:
            size_kb = size_result[0] / 1024
            size_mb = size_kb / 1024
            print(f"Примерный размер: {size_kb:.2f} KB ({size_mb:.2f} MB)")

def get_database_summary(db_path: str):
    """
    Получить сводку по всей базе данных
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        print(f"\n{'='*60}")
        print(f"СВОДКА БАЗЫ ДАННЫХ: {db_path}")
        print(f"{'='*60}")
        
        # Получить все таблицы
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = cursor.fetchall()
        
        print(f"\nВсего таблиц: {len(tables)}")
        
        summary = []
        for table in tables:
            table_name = table[0]
            
            # Пропускаем системные таблицы
            if table_name.startswith('sqlite_'):
                continue
                
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            column_count = len(cursor.fetchall())
            
            summary.append([table_name, row_count, column_count])
        
        # Сортируем по количеству строк
        summary.sort(key=lambda x: x[1], reverse=True)
        
        print(tabulate(
            summary, 
            headers=["Таблица", "Строк", "Столбцов"],
            tablefmt="grid"
        ))

# Использование
if __name__ == "__main__":
    db_path = "/home/alex/temp/price_database.db"
    
    # Получить сводку по всей базе
    get_database_summary(db_path)
    
    # Получить структуру конкретных таблиц
    tables_to_check = ["BasePrices", "AdditionalOptions", 
                      "OptionConditions", "ConditionProperties"]
    
    for table in tables_to_check:
        get_table_structure(db_path, table)