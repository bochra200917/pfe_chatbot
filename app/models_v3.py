# app/models_v3.py
from pydantic import BaseModel
from typing import List, Dict, Optional


class SQLQuery(BaseModel):

    intent: str
    sql: str
    params: Dict[str, str]


class ChatbotResponse(BaseModel):

    table: List[Dict]
    summary: str
    metadata: Dict


class LLMQuery(BaseModel):

    intent: str
    tables: List[str]
    columns: List[str]
    filters: Dict
    limit: int