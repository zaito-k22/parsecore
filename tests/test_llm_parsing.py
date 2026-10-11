import pytest

from app.exceptions.invoice import LLMExtractionError
from app.services.llm.parsing import parse_llm_json


def test_plain_json():
    assert parse_llm_json('{"a": 1}') == {"a": 1}


def test_markdown_fence():
    assert parse_llm_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_text_around_json():
    assert parse_llm_json('Aquí está:\n{"a": {"b": 2}}\nListo.') == {"a": {"b": 2}}


@pytest.mark.parametrize(
    "raw", ["", "   ", "sin json", "[1, 2]", "{roto", '"texto"', "null"]
)
def test_invalid_raises(raw):
    with pytest.raises(LLMExtractionError):
        parse_llm_json(raw)
