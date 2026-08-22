from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel


class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate raw text response."""
        pass

    @abstractmethod
    def generate_json(self, prompt: str, schema: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
        """Generate structured JSON adhering to the Pydantic schema."""
        pass
