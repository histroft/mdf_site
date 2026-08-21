from pydantic import BaseModel, validator
from typing import Dict, List, Optional, Any

class ModelCharacteristicsRequest(BaseModel):
    model: str
    
    @validator('model')
    def model_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Модель не может быть пустой')
        return v.strip()

class CheckRequest(BaseModel):
    model: str
    characteristics: Dict[str, Any]
    
    @validator('characteristics')
    def validate_characteristics(cls, v):
        if not isinstance(v, dict):
            raise ValueError('Характеристики должны быть словарем')
        return v

class OrderRequest(BaseModel):
    data: Dict[str, Any]
    
    @validator('data')
    def validate_order_data(cls, v):
        required_fields = ['model', 'characteristics']
        for field in required_fields:
            if field not in v:
                raise ValueError(f'Отсутствует обязательное поле: {field}')
        return v

class LoginRequest(BaseModel):
    username: str
    password: str
    
    @validator('username')
    def username_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Имя пользователя не может быть пустым')
        return v.strip()
    
    @validator('password')
    def password_not_empty(cls, v):
        if not v:
            raise ValueError('Пароль не может быть пустым')
        return v

class OrderResponse(BaseModel):
    success: bool
    contract_id: Optional[str] = None
    error: Optional[str] = None