
import sqlite3
import xml.etree.ElementTree as ET

def update_price_db_from_xml(xml_file_path, sqlite_db_path):
    """
    Загружает данные из XML и сохраняет в уже созданную базу данных SQLite,
    избегая дублирования записей.
    """

    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    # Парсим и вставляем базовые цены
    base_prices_section = root.find(".//ЦеныНоменклатуры")
    if base_prices_section is not None:
        for nomenclature in base_prices_section.findall("Номенклатура"):
            registrar = nomenclature.attrib.get("Регистратор")
            rownum = int(nomenclature.attrib.get("НомерСтроки", 0))
            price_type = nomenclature.attrib.get("ТипЦен")
            nomencl = nomenclature.attrib.get("Номенклатура")
            currency = nomenclature.attrib.get("Валюта")
            price_str = nomenclature.attrib.get("Цена", "0").replace(',', '.')
            try:
                price = float(price_str)
            except ValueError:
                price = 0.0
            unit = nomenclature.attrib.get("ЕдиницаИзмерения")
            discount_str = nomenclature.attrib.get("ПроцентСкидкиНаценки", "0").replace(',', '.')
            try:
                discount = float(discount_str)
            except ValueError:
                discount = 0.0
            price_calc = nomenclature.attrib.get("СпособРасчетаЦены")

            # Проверяем есть ли уже такая запись
            cursor.execute('''
                SELECT ID FROM BasePrices 
                WHERE Nomenclature = ? AND PriceType = ? AND RowNumber = ?
            ''', (nomencl, price_type, rownum))
            if cursor.fetchone() is None:
                cursor.execute('''
                    INSERT INTO BasePrices 
                    (Registrar, RowNumber, PriceType, Nomenclature, Currency, Price, Unit, DiscountPercent, PriceCalcMethod)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (registrar, rownum, price_type, nomencl, currency, price, unit, discount, price_calc))
    conn.commit()

    # Загружаем ДопОпции
    for dop_op in root.findall(".//ДопОпция"):
        option_id = dop_op.attrib.get("КодОпции")
        registrar = dop_op.attrib.get("Регистратор")
        row_number = dop_op.attrib.get("НомерСтроки")
        if row_number is not None:
            try:
                row_number = int(row_number)
            except ValueError:
                row_number = 0
        else:
            row_number = 0
        name = dop_op.attrib.get("НаименованиеОпции")
        is_percent_str = dop_op.attrib.get("ПроцентОтБазовойЦены", "false")
        is_percent = is_percent_str.strip().lower() == "true"
        nomenclature = dop_op.attrib.get("Номенклатура")
        price_type = dop_op.attrib.get("ТипЦен")
        price_str = dop_op.attrib.get("Цена", "0").replace(',', '.')
        try:
            price = float(price_str)
        except ValueError:
            price = 0.0

        # Проверяем, есть ли уже такая доп.опция
        cursor.execute('''
            SELECT ID FROM AdditionalOptions
            WHERE OptionID = ? AND Nomenclature = ? AND RowNumber = ?
        ''', (option_id, nomenclature, row_number))
        row = cursor.fetchone()
        if row is None:
            cursor.execute('''
                INSERT INTO AdditionalOptions 
                (OptionID, Nomenclature, Registrar, RowNumber, Name, IsPercentOfBasePrice, PriceType, Price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (option_id, nomenclature, registrar, row_number, name, is_percent, price_type, price))
            additional_option_id = cursor.lastrowid
        else:
            additional_option_id = row[0]

        # Парсим условия, если есть
        conditions = dop_op.findall("УсловияХарактеристики")
        if conditions:
            for condition in conditions:
                cond_name = condition.attrib.get("НаименованиеУсловия")
                cond_logic_or_str = condition.attrib.get("УсловиеИЛИ", "false")
                cond_logic_or = cond_logic_or_str.strip().lower() == "true"
                cond_not_str = condition.attrib.get("УсловиеНЕ", "false")
                cond_not = cond_not_str.strip().lower() == "true"
                cond_text = condition.attrib.get("УсловиеТЕКСТ")

                # Проверяем есть ли уже такое условие для этой доп.опции
                cursor.execute('''
                    SELECT ConditionID FROM OptionConditions
                    WHERE AdditionalOptionID = ? AND ConditionName = ?
                ''', (additional_option_id, cond_name))
                cond_row = cursor.fetchone()
                if cond_row is None:
                    cursor.execute('''
                        INSERT INTO OptionConditions 
                        (AdditionalOptionID, ConditionName, ConditionLogicOR, ConditionNot, ConditionText)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (additional_option_id, cond_name, cond_logic_or, cond_not, cond_text))
                    condition_id = cursor.lastrowid
                else:
                    condition_id = cond_row[0]

                cond_props = condition.findall("ТЧУсловие")
                for cond_prop in cond_props:
                    prop_name = cond_prop.attrib.get("Свойство")
                    val = cond_prop.attrib.get("Значение")
                    comp_type = cond_prop.attrib.get("ВидСравнения", "")

                    # Проверяем есть ли уже такое свойство условия
                    cursor.execute('''
                        SELECT ConditionPropertyID FROM ConditionProperties
                        WHERE ConditionID = ? AND PropertyName = ? AND Value = ? AND ComparisonType = ?
                    ''', (condition_id, prop_name, val, comp_type))
                    if cursor.fetchone() is None:
                        cursor.execute('''
                            INSERT INTO ConditionProperties (ConditionID, PropertyName, Value, ComparisonType) 
                            VALUES (?, ?, ?, ?)
                        ''', (condition_id, prop_name, val, comp_type))
    conn.commit()
    conn.close()

if __name__=='__main__':
    from config import Config
    xml_path = Config.PRICE
    db_path = Config.PATH_TO_PRICE_DB
    update_price_db_from_xml(xml_path, db_path)
