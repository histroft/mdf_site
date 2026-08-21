"""
Диагностика опций 'НЕСТАНДАРТ размер' для модели DELTA 100 MP
"""

import sys
import sqlite3
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config import Config

def check_nonstandard_options():
    db_path = Config.NEW_PATH_TO_PRICE_DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    model = "DELTA 100 MP"
    price_type = "РРЦ"
    
    print("=" * 80)
    print(f"ОПЦИИ 'НЕСТАНДАРТ размер' для {model} / {price_type}")
    print("=" * 80)
    
    # Ищем все опции с названием "НЕСТАНДАРТ размер"
    cursor.execute('''
        SELECT ID, OptionID, Name, Price, IsPercentOfBasePrice, PriceType
        FROM AdditionalOptions
        WHERE Nomenclature = ? 
        AND PriceType = ?
        AND Name LIKE '%НЕСТАНДАРТ размер%'
    ''', (model, price_type))
    
    options = cursor.fetchall()
    
    if not options:
        print("\n❌ Опции не найдены!")
        conn.close()
        return
    
    print(f"\n📦 Найдено опций: {len(options)}")
    
    for opt in options:
        opt_id, option_id, name, price, is_percent, pt = opt
        print(f"\n📌 ID: {opt_id}")
        print(f"   Код: {option_id}")
        print(f"   Название: {name}")
        print(f"   Цена: {price}")
        print(f"   Процент: {'Да' if is_percent else 'Нет'}")
        print(f"   Тип цен: {pt}")
        
        # Получаем условия
        cursor.execute('''
            SELECT ConditionID, ConditionName, ConditionLogicOR, ConditionNot, ConditionText
            FROM OptionConditions
            WHERE AdditionalOptionID = ?
        ''', (opt_id,))
        
        conditions = cursor.fetchall()
        
        if conditions:
            print(f"   Условий: {len(conditions)}")
            for cond in conditions:
                cond_id, cond_name, cond_or, cond_not, cond_text = cond
                print(f"\n   ┌─ Условие ID {cond_id}")
                print(f"   │  Название: {cond_name}")
                print(f"   │  OR: {bool(cond_or)}")
                print(f"   │  NOT: {bool(cond_not)}")
                print(f"   │  Текст: {cond_text if cond_text else 'Нет'}")
                
                # Получаем свойства
                cursor.execute('''
                    SELECT PropertyName, Value, ComparisonType
                    FROM ConditionProperties
                    WHERE ConditionID = ?
                ''', (cond_id,))
                
                props = cursor.fetchall()
                if props:
                    print(f"   │  Свойства:")
                    for prop in props:
                        prop_name = prop[0].split(' (Справочник')[0]
                        print(f"   │    • {prop_name} {prop[2] if prop[2] else '='} '{prop[1]}'")
        else:
            print(f"   Условий: НЕТ (безусловная опция)")
            print(f"   ⚠️ Эта опция будет применяться ВСЕГДА, если нет условий!")
    
    # Проверяем, какие опции должны были примениться при ширине 950 и высоте 2300
    print("\n" + "=" * 80)
    print("ПРОВЕРКА С УЧЁТОМ РАЗМЕРОВ")
    print(f"Ширина: 950, Высота: 2300")
    print("=" * 80)
    
    width = 950
    height = 2300
    
    for opt in options:
        opt_id = opt[0]
        
        cursor.execute('''
            SELECT cp.PropertyName, cp.Value, cp.ComparisonType
            FROM ConditionProperties cp
            JOIN OptionConditions oc ON cp.ConditionID = oc.ConditionID
            WHERE oc.AdditionalOptionID = ?
        ''', (opt_id,))
        
        props = cursor.fetchall()
        
        if props:
            print(f"\n📌 Опция ID {opt_id}:")
            for prop in props:
                prop_name, value, comp_type = prop
                if 'ширина' in prop_name.lower():
                    cond_val = int(value)
                    if width >= cond_val if '>=' in comp_type else width > cond_val:
                        print(f"   ✅ Ширина {width} >= {cond_val} - условие выполнено")
                    else:
                        print(f"   ❌ Ширина {width} < {cond_val} - условие НЕ выполнено")
                elif 'высота' in prop_name.lower():
                    cond_val = int(value)
                    if height >= cond_val if '>=' in comp_type else height > cond_val:
                        print(f"   ✅ Высота {height} >= {cond_val} - условие выполнено")
                    else:
                        print(f"   ❌ Высота {height} < {cond_val} - условие НЕ выполнено")
    
    conn.close()

if __name__ == '__main__':
    check_nonstandard_options()