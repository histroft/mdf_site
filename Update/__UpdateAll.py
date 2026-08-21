import logging
from CreateDB import create_database
from ParseXML import parse_xml_and_update_db
from SaveUncToGoogle import find_specific_incompatibilities_to_gsheet
from _update_manuals_table import update_manual_incompatibilities
from _update_models_table import find_and_save_global_incompatibilities_models
from _update_non_models_table import find_and_save_global_incompatibilities_non_models
from UpdateMDF import UpdateMDFDatabase
from UpdatePriceDB_2 import update_price_db_from_xml
from Delete_BD import delete_database_file

# Новые пути под ваш проект
from config import Config

LOG_FILE = "update.log"
logging.basicConfig(
    filename=LOG_FILE,
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    encoding="utf-8-sig"
)


def update_all():
    # Пути из Config
    doors_db = Config.DATABASE  # database/doors.db
    mdf_db = Config.MDF_DB      # database/mdf_pic.db
    price_db = Config.PATH_TO_PRICE_DB  # database/price_database.db
    new_price_db = Config.NEW_PATH_TO_PRICE_DB  # database/price_database.db
    
    
    # Внешние ресурсы
    google_url = Config.GOOGLE_URL
    xml_file = Config.XML  # Assortment-TOREX-777.xml
    price_xml = Config.PRICE  # TOREX-Assortment-Prices.xml
    
    try:
        # Удалить старую базу
        logging.info("Удаляем старую базу")
        delete_database_file(doors_db)

        logging.info("Создание базы данных дверей...")
        create_database(doors_db)

        logging.info("Начало обновления базы данных...")

        # Обновляем БД дверей
        logging.info("Шаг 1: Обновление базы данных дверей.")
        parse_xml_and_update_db(doors_db, xml_file)
        logging.info("База данных дверей успешно обновлена.")

        # Обновляем таблицу ручных несовместимостей
        logging.info("Шаг 2: Обновление таблицы РУЧНЫХ несовместимостей из Google.")
        update_manual_incompatibilities(google_url, doors_db, batch_size=3000)
        logging.info("Таблица ручных несовместимостей успешно обновлена.")
        
        # Обновляем таблицу несовместимостей из Google
        logging.info('Обновление таблицы несовместимостей из Google')
        find_specific_incompatibilities_to_gsheet(doors_db, google_url)
        
        # Обновляем БД по несовместимостям с моделями из Google
        logging.info("Обновляем БД по несовместимостям с моделями из Google")
        find_and_save_global_incompatibilities_models(doors_db, google_url)
        
        # Обновляем БД МДФ
        logging.info("Шаг 3: Обновление базы данных МДФ.")
        mdf_update = UpdateMDFDatabase(mdf_db)

        if not mdf_update.clear_database():
            logging.warning("Предупреждение: не удалось очистить базу данных МДФ.")
        else:
            logging.info("База данных МДФ очищена.")

        if not mdf_update.import_from_gsheet(google_url):
            logging.error("Ошибка: не удалось обновить БД МДФ из Google Sheets.")
            exit(1)
        else:
            logging.info("База данных МДФ успешно обновлена.")
        
        # Обновляем базу с Peep Offset
        mdf_update.import_peep_offset(google_url)
        
        # Обновляем БД Цены
        logging.info('Обновление цен')
        #update_price_db_from_xml(price_xml, price_db)
        base_price_xml=Config.BASE_PRICE_XML
        all_prices_xml=Config.ALL_PRICES_XML
        update_price_db_from_xml(base_price_xml, all_prices_xml, new_price_db)
        
        
        logging.info("Обновление завершено успешно.")
        
    except Exception as e:
        logging.exception(f"Произошла ошибка во время выполнения обновления: {e}")


if __name__ == "__main__":
    update_all()