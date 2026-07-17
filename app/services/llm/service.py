import json
import os
from pathlib import Path

from ollama import Client


class LLMService:
    def __init__(self):
        print("Inicializando Ollama...")

        ollama_host = os.getenv(
            "OLLAMA_HOST",
            "http://localhost:11434"
        )

        self.client = Client(host=ollama_host)

        self.model = "gemma3:4b"

    def extract_document(self, text: str):
        """
        Convierte el texto obtenido por el OCR
        en un documento estructurado.
        """

        prompt = self._build_prompt(text)

        response = self._chat(prompt)

        response = self._clean_json(response)

        return json.loads(response)

    def _chat(self, prompt: str):
        """
        Envía el prompt al modelo.
        """

        response = self.client.chat(
            model=self.model,
            format="json",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response["message"]["content"]

    def _clean_json(self, response: str):
        """
        Limpia la respuesta del modelo
        en caso de que venga envuelta
        en Markdown.
        """

        return (
            response
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

    def _build_prompt(self, text: str):
        """
        Carga la plantilla del prompt
        y reemplaza {TEXT}.
        """

        prompt_path = (
            Path(__file__).parents[2]
            / "prompts"
            / "invoice_prompt.txt"
        )

        prompt = prompt_path.read_text(
            encoding="utf-8"
        )

        return prompt.replace("{TEXT}", text)


llm_service = LLMService()