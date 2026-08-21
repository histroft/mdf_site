import os
import sqlite3

import gspread
from oauth2client.service_account import ServiceAccountCredentials


class UpdateMDFDatabase:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = None

    def authorize_gspread(self):
        print("Starting authorized client...")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        path_to_file = str(os.path.dirname(os.path.abspath(__file__))) + '/credentials.json'
        creds = ServiceAccountCredentials.from_json_keyfile_name(path_to_file, scope)
        client = gspread.authorize(creds)
        print("Connect succesful")
        return client

    def connect(self):
        """Устанавливает соединение с базой данных"""
        self.conn = sqlite3.connect(self.db_name)
        self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn.cursor()

    def close(self):
        """Закрывает соединение с базой данных"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        """Создает таблицы в базе данных"""
        cursor = self.connect()
        try:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS exterior_finishes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_type TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                center_placement TEXT NOT NULL CHECK(center_placement IN ('ДА', 'НЕТ')),
                side_placement TEXT NOT NULL CHECK(side_placement IN ('ДА', 'НЕТ')),
                UNIQUE(material_type, pattern_name)
            )''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS interior_finishes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_type TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                center_placement TEXT NOT NULL CHECK(center_placement IN ('ДА', 'НЕТ')),
                side_placement TEXT NOT NULL CHECK(side_placement IN ('ДА', 'НЕТ')),
                UNIQUE(material_type, pattern_name)
            )''')

            self.conn.commit()
            print("Таблицы успешно созданы")
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при создании таблиц: {e}")
            return False
        finally:
            self.close()

    def clear_database(self):
        """Очищает таблицы"""
        try:
            cursor = self.connect()
            cursor.execute("DELETE FROM exterior_finishes")
            cursor.execute("DELETE FROM interior_finishes")
            self.conn.commit()
            print("База данных очищена")
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при очистке: {e}")
            return False
        finally:
            self.close()

    
    def import_peep_offset(self, sheet_url):
        sheet_name = "Глазок сбоку"
        try:
            client = self.authorize_gspread()
            print("Try to connect...")

            # Открываем таблицу
            sh = client.open_by_url(sheet_url)
            print("Connected to Google")

            wks = sh.worksheet(sheet_name)

            # Получаем все строки с таблицы
            all_values = wks.get_all_values()
            if len(all_values) < 2:
                print("Таблица 'Глазок сбоку' пуста или содержит только заголовок")
                return False

            cursor = self.connect()  # Предполагаем, что этот метод возвращает курсор

            insert_count = 0
            for row_idx, row in enumerate(all_values[1:], start=2):  # пропускаем заголовок
                try:
                    # Столбец A - рисунок наружной панели (индекс 0)
                    outside_pic = row[0].strip() if len(row) > 0 else ''

                    # Столбец D - рисунок внутренней панели (индекс 3)
                    inside_pic = row[3].strip() if len(row) > 3 else ''

                    cursor.execute('''
                        INSERT OR REPLACE INTO peep_offset (outside_pic, inside_pic)
                        VALUES (?, ?)
                    ''', (outside_pic, inside_pic))
                    insert_count += 1

                except Exception as e:
                    print(f"Ошибка обработки строки {row_idx}: {e}")

            self.conn.commit()
            print(f"Импорт из листа 'Глазок сбоку' завершён, обработано строк: {insert_count}")
            return True

        except Exception as e:
            print(f"Фатальная ошибка импорта глазка сбоку: {e}")
            if self.conn:
                self.conn.rollback()
            return False

        finally:
            self.close()

    
    def import_from_gsheet(self, sheet_url):
        """Импортирует данные из Google Sheets"""

        sheet_name = "Рисунки_Совместимость"
        # google_url = 'https://docs.google.com/spreadsheets/d/1aF6ZJNr47jAI1Gjt-EGOU8Se-kYNs9F-4KNQ_UQJG4k/edit?gid=288908521#gid=288908521'

        try:

            client = self.authorize_gspread()
            print("Try to connect...")

            # Открываем таблицу
            sh = client.open_by_url(sheet_url)
            print("Connected to Google")

            wks = sh.worksheet(sheet_name)

            # Получаем данные как список списков
            data = wks.get_all_values()
            print("Получение данных о размере таблицы...")
            all_values = wks.get_all_values()
            total_rows = len(all_values)
            print(f"Всего строк для обработки: {total_rows - 1}")  # Минус заголовок

            # Подключаемся к БД
            cursor = self.connect()

            ext_count = 0
            int_count = 0

            for row_idx, row in enumerate(data[1:], start=2):  # Пропускаем заголовок (начинаем с индекса 2)
                try:
                    # Наружная отделка (столбцы A-D)
                    if len(row) >= 4:
                        material = str(row[0])
                        pattern = str(row[1])
                        center = str(row[2]).strip().upper() if row[2] else 'НЕТ'
                        side = str(row[3]).strip().upper() if row[3] else 'НЕТ'

                        # Проверяем валидность данных перед вставкой
                        # if (material and pattern and
                        #         center in ('ДА', 'НЕТ') and
                        #         side in ('ДА', 'НЕТ')):
                        cursor.execute('''
                        INSERT OR REPLACE INTO exterior_finishes 
                        (material_type, pattern_name, center_placement, side_placement)
                        VALUES (?, ?, ?, ?)
                        ''', (material, pattern, center, side))
                        ext_count += 1
                        # else:
                        #     print('DON_T ADD', material, pattern, center, side)

                    # Внутренняя отделка (столбцы H-K)
                    if len(row) >= 11:
                        material = str(row[7])
                        pattern = str(row[8])
                        center = str(row[9]).strip().upper() if row[9] else 'НЕТ'
                        side = str(row[10]).strip().upper() if row[10] else 'НЕТ'

                        # if (material and pattern and
                        #         center in ('ДА', 'НЕТ') and
                        #         side in ('ДА', 'НЕТ')):
                        cursor.execute('''
                        INSERT OR REPLACE INTO interior_finishes 
                        (material_type, pattern_name, center_placement, side_placement)
                        VALUES (?, ?, ?, ?)
                        ''', (material, pattern, center, side))
                        int_count += 1

                except Exception as e:
                    print(f"Ошибка в строке {row_idx}: {e}")
                    continue

            self.conn.commit()
            print(f"Импорт завершен. Добавлено:")
            print(f"- Наружных отделок: {ext_count}")
            print(f"- Внутренних отделок: {int_count}")
            return True

        except Exception as e:
            print(f"Фатальная ошибка импорта: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            self.close()


if __name__=='__main__':
    from config import Config
    db_name = Config.MDF_DB
    url = Config.GOOGLE_URL
    update = UpdateMDFDatabase(db_name)
    update.import_peep_offset(url)