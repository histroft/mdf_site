import json
from typing import Dict, List, Any, Tuple
from database.connection import DatabaseConnection
import logging

logger = logging.getLogger(__name__)

class ModelService:
    def __init__(self, db_path: str, mdf_db_path: str, no_peep_file: str):
        self.db = DatabaseConnection(db_path)
        self.mdf_db = DatabaseConnection(mdf_db_path)
        self.no_peep_models = self._load_no_peep_models(no_peep_file)
    
    def _load_no_peep_models(self, file_path: str) -> set:
        """Загрузка списка моделей без глазка"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('models', []))
        except FileNotFoundError:
            logger.warning(f"File {file_path} not found, using empty set")
            return set()
    
    def get_model_list(self) -> List[str]:
        """Получение списка моделей"""
        query = "SELECT DISTINCT model FROM doors ORDER BY model"
        rows = self.db.execute_query(query)
        return [row['model'] for row in rows]
    
    def get_model_characteristics(self, model: str) -> List[Dict]:
        """Получение характеристик модели"""
        query = """
            SELECT characteristic, standard_value, possible_values 
            FROM doors 
            WHERE model = ? 
            ORDER BY characteristic
        """
        rows = self.db.execute_query(query, (model,))
        return [dict(row) for row in rows]
    
    def check_possible_make(self, data: Dict) -> Tuple[bool, str]:
        """Проверка возможности изготовления"""
        # Здесь должна быть бизнес-логика проверки
        try:
            # Имитация проверки
            return True, "OK"
        except Exception as e:
            logger.error(f"Error in check_possible_make: {e}")
            return False, str(e)
    
    def is_peep_standard(self, model: str) -> bool:
        """Проверка наличия глазка в модели"""
        return model not in self.no_peep_models
    
    def check_peep_offset(self, out_pic: str, in_pic: str) -> bool:
        """Проверка смещения глазка"""
        query = """
            SELECT 1 FROM peep_offset
            WHERE outside_pic = ? OR inside_pic = ?
            LIMIT 1
        """
        result = self.mdf_db.execute_query(query, (out_pic, in_pic))
        return bool(result)