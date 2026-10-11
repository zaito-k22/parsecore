import json

from app.exceptions.invoice import LLMExtractionError


def parse_llm_json(raw: str) -> dict:
    """
    Convierte la respuesta cruda del modelo en un dict.

    Tolera bloques Markdown y texto alrededor del JSON. Lanza
    LLMExtractionError si no se puede obtener un objeto JSON.
    """

    if not raw or not raw.strip():
        raise LLMExtractionError("Respuesta vacía del modelo")

    text = (
        raw.replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        data = json.loads(text)

    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end <= start:
            raise LLMExtractionError("La respuesta no contiene JSON")

        try:
            data = json.loads(text[start : end + 1])

        except json.JSONDecodeError as exc:
            raise LLMExtractionError("JSON inválido") from exc

    if not isinstance(data, dict):
        raise LLMExtractionError("El JSON no es un objeto")

    return data
