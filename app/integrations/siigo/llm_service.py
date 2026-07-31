from pathlib import Path

import ollama


class SiigoLLMService:

    def __init__(self):
        self.model = "qwen3:8b"

        prompt_path = (
            Path(__file__).parent.parent.parent
            / "prompts"
            / "siigo_invoice_schema.txt"
        )

        self.prompt = prompt_path.read_text(
            encoding="utf-8",
        )

    def generate(
        self,
        ocr_text: str,
    ) -> str:

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": self.prompt.replace(
                        "{TEXT}",
                        ocr_text,
                    ),
                }
            ],
        )

        return response["message"]["content"]