import os
import json
import logging
from typing import Optional, Type
import httpx
from pydantic import BaseModel, ValidationError
from app.llm.base import LLMProvider

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

        if not self.api_key:
            logger.warning("GROQ_API_KEY is not set. Groq calls will fail unless configured.")

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(self.api_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def generate_json(self, prompt: str, schema: Type[BaseModel], system_prompt: Optional[str] = None) -> BaseModel:
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        base_system = system_prompt or "You are an expert PO agent. Respond ONLY in raw valid JSON."
        full_system = (
            f"{base_system}\n\n"
            f"You MUST return valid JSON matching this exact Pydantic schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do not include any explanation outside the JSON block."
        )

        current_prompt = prompt
        max_retries = 3

        for attempt in range(max_retries):
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": current_prompt}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }

            try:
                with httpx.Client(timeout=45.0) as client:
                    resp = client.post(self.api_url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed_dict = json.loads(content)
                    return schema.model_validate(parsed_dict)
            except (httpx.HTTPError, json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Groq generation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to generate valid JSON adhering to schema after {max_retries} retries: {e}")
                current_prompt = f"{prompt}\n\nYour previous attempt failed validation with error:\n{e}\nPlease correct the JSON output."
