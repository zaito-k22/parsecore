import logging
from pathlib import Path

from ollama import Client

from app.core.config import settings
from app.services.llm.parsing import parse_llm_json

logger = logging.getLogger(__name__)

PROMPT_PATH = (
    Path(__file__).parents[2] / "prompts" / "invoice_prompt.txt"
)


class LLMService:
    def __init__(self):
        logger.info(
            "Inicializando Ollama (host=%s, modelo=%s)",
            settings.ollama_host,
            settings.ollama_model,
        )

        self.client = Client(
            host=settings.ollama_host,
            timeout=settings.ollama_timeout,
        )

        self.model = settings.ollama_model

    def extract_document(self, text: str) -> dict:
        """
        Convierte el texto obtenido por el OCR en un documento
        estructurado. Lanza LLMExtractionError si la respuesta
        no es utilizable.
        """

        response = self._chat(self._build_prompt(text))

        return parse_llm_json(response)

    def _chat(self, prompt: str) -> str:
        response = self.client.chat(
            model=self.model,
            format="json",
            options={"temperature": 0},
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response["message"]["content"]

    def _build_prompt(self, text: str) -> str:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")

        return prompt.replace("{TEXT}", text)


llm_service = LLMService()
