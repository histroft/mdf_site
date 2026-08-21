"""
Константы для экономического расчета
"""

class PriceConstants:
    """Константы для расчета цен"""
    
    # Версия
    VERSION = '1.0.0'
    # Типы цен
    DEFAULT_PRICE_TYPE = "Цены ТД ТОРЭКС"
    
    # Ключи запроса
    MODEL_KEY = 'model'
    PRICE_TYPE_KEY = 'price_type'
    PERCENT_KEY = 'percent_base_price'
    OPTIONS_KEY = 'advance_options'
    
    # Поля в БД
    BASE_PRICE_TABLE = 'BasePrices'
    ADDITIONAL_OPTIONS_TABLE = 'AdditionalOptions'
    OPTION_CONDITIONS_TABLE = 'OptionConditions'
    CONDITION_PROPERTIES_TABLE = 'ConditionProperties'
    
    # Колонки таблиц
    COL_ID = 'ID'
    COL_NOMENCLATURE = 'Nomenclature'
    COL_PRICE_TYPE = 'PriceType'
    COL_PRICE = 'Price'
    COL_OPTION_ID = 'OptionID'
    COL_NAME = 'Name'
    COL_IS_PERCENT = 'IsPercentOfBasePrice'
    COL_CONDITION_ID = 'ConditionID'
    COL_CONDITION_OR = 'ConditionLogicOR'
    COL_CONDITION_NOT = 'ConditionNot'
    COL_CONDITION_TEXT = 'ConditionText'
    COL_PROPERTY_NAME = 'PropertyName'
    COL_VALUE = 'Value'
    COL_COMPARISON_TYPE = 'ComparisonType'
    
    # 👇 ДОБАВЬТЕ ЭТУ СТРОКУ - правильное название внешнего ключа
    COL_ADDITIONAL_OPTION_ID = 'AdditionalOptionID'  # Внешний ключ к таблице AdditionalOptions
    
    # Операторы сравнения
    OP_EQUAL = '='
    OP_NOT_EQUAL = '<>'
    OP_GREATER = '>'
    OP_LESS = '<'
    OP_GREATER_EQUAL = '>='
    OP_LESS_EQUAL = '<='
    
    # Шаблоны сообщений
    MSG_OPTION_APPLIED = "✅ Опция '{name}' применена"
    MSG_OPTION_SKIPPED = "⏭️ Опция '{name}' пропущена"
    MSG_TOTAL_PRICE = "ИТОГОВАЯ ЦЕНА: {price:.2f}"
    MSG_PRICE_TYPE = "Тип цен: {price_type}"
    MSG_BASE_PRICE = "Цена модели '{model}' (тип: '{price_type}'): {price:.2f}, наценка {percent}%"
    MSG_OPTION_PRICE = "   Сумма: {price:.2f}, изменение: +{change:.2f}"
    
    # Разделители
    SEPARATOR_LINE = "=" * 18
    SEPARATOR_SECTION = "=" * 60
    
    # Регулярные выражения
    RE_CONDITION_IF = r"Если\s*(.+?)\s+Тогда"
    RE_CONDITION_SPLIT = r'\bили\b'
    RE_CONDITION_AND = r'\bи\b'
    RE_CONDITION_SIMPLE = r'(.+?)(>=|<=|<>|>|<|=)(.+)'
    RE_PREFIX_NUM = r'^\d+_'


class PriceErrors:
    """Сообщения об ошибках"""
    MODEL_NOT_FOUND = "Модель '{model}' не найдена"
    MODEL_KEY_MISSING = "Ключ 'model' отсутствует в запросе"
    NO_PRICE_FOUND = "Базовая цена для модели '{model}' не найдена"
    NO_PRICE_TYPES = "Нет доступных типов цен для модели '{model}'"
    INVALID_COMPARISON = "Ошибка сравнения значений"
    DB_ERROR = "Ошибка базы данных: {error}"