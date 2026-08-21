import sqlite3


def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создаем таблицы
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS models (
        model_id INTEGER PRIMARY KEY,
        model_name TEXT UNIQUE NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS variants (
        variant_id INTEGER PRIMARY KEY,
        model_id INTEGER,
        unique_combination TEXT UNIQUE NOT NULL,
        FOREIGN KEY (model_id) REFERENCES models (model_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties (
        property_id INTEGER PRIMARY KEY,
        property_name TEXT UNIQUE NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS characteristics (
        char_id INTEGER PRIMARY KEY,
        property_id INTEGER,
        variant_id INTEGER,
        value TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties (property_id),
        FOREIGN KEY (variant_id) REFERENCES variants (variant_id),
        UNIQUE (property_id, variant_id, value)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS options (
        option_id INTEGER PRIMARY KEY,
        option_code TEXT UNIQUE NOT NULL,
        option_name TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS model_options (
        model_id INTEGER,
        option_id INTEGER,
        PRIMARY KEY (model_id, option_id),
        FOREIGN KEY (model_id) REFERENCES models (model_id),
        FOREIGN KEY (option_id) REFERENCES options (option_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS incompatibilities (
        incompatibility_id INTEGER PRIMARY KEY,
        model_id INTEGER,
        property1_id INTEGER,
        value1 TEXT,
        property2_id INTEGER,
        value2 TEXT,
        FOREIGN KEY (model_id) REFERENCES models (model_id),
        FOREIGN KEY (property1_id) REFERENCES properties (property_id),
        FOREIGN KEY (property2_id) REFERENCES properties (property_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS incompatibilities_non_models (
        incompatibility_id INTEGER PRIMARY KEY,
        property1_id INTEGER,
        value1 TEXT,
        property2_id INTEGER,
        value2 TEXT,
        FOREIGN KEY (property1_id) REFERENCES properties (property_id),
        FOREIGN KEY (property2_id) REFERENCES properties (property_id)
    )
    ''')

    conn.commit()
    conn.close()




if __name__ == '__main__':
    db_path = '/home/alex/temp/doors.db'
    create_database(db_path)
