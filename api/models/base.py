from typing import Any, Dict
from pydantic import BaseModel

class DocOut(BaseModel):
    # Гибкая модель: принимает любые ключи/значения
    # (для Swagger укажем response_model=List[Dict[str, Any]])
    pass  # в роутерах будем отдавать просто dict