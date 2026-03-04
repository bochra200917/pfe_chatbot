from pydantic import BaseModel, Field
from typing import Dict, Any, List

class LLMQuery(BaseModel):
    intent: str = Field(..., description="Nom du template SQL")
    tables: List[str]
    columns: List[str]
    filters: Dict[str, Any]
    limit: int = Field(default=100, ge=1, le=500)