"""
Tests for LLM Extractor module.

Tests are split into:
- Unit tests: mock the OpenAI API, test prompt building, type coercion, validation
- Integration tests: hit the real API (skipped unless OPENAI_API_KEY is set)
"""
import json
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from features.modules.definitions.transform.llm_extractor import LlmExtractor, LlmExtractorConfig


# ============================================================================
# Unit Tests (no API key needed)
# ============================================================================

class TestLlmExtractorConfig:
    def test_valid_config(self):
        cfg = LlmExtractorConfig(
            prompt_template="Extract from: {text}",
            model="gpt-4o-mini",
            temperature=0.0,
        )
        assert cfg.prompt_template == "Extract from: {text}"

    def test_defaults(self):
        cfg = LlmExtractorConfig(prompt_template="test")
        assert cfg.model == "gpt-4o-mini"
        assert cfg.temperature == 0.0


class TestTypeCoercion:
    def test_str(self):
        assert LlmExtractor._coerce_value("hello", "str", "f") == "hello"
        assert LlmExtractor._coerce_value(123, "str", "f") == "123"

    def test_int(self):
        assert LlmExtractor._coerce_value(42, "int", "f") == 42
        assert LlmExtractor._coerce_value("42", "int", "f") == 42
        assert LlmExtractor._coerce_value("42.7", "int", "f") == 42

    def test_float(self):
        assert LlmExtractor._coerce_value(3.14, "float", "f") == 3.14
        assert LlmExtractor._coerce_value("3.14", "float", "f") == 3.14

    def test_bool(self):
        assert LlmExtractor._coerce_value(True, "bool", "f") is True
        assert LlmExtractor._coerce_value("true", "bool", "f") is True
        assert LlmExtractor._coerce_value("false", "bool", "f") is False
        assert LlmExtractor._coerce_value("yes", "bool", "f") is True

    def test_datetime_iso(self):
        result = LlmExtractor._coerce_value("2026-04-05T23:00:00", "datetime", "f")
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 4
        assert result.hour == 23

    def test_datetime_short_iso(self):
        result = LlmExtractor._coerce_value("2026-04-05T23:00", "datetime", "f")
        assert isinstance(result, datetime)

    def test_datetime_date_only(self):
        result = LlmExtractor._coerce_value("2026-04-05", "datetime", "f")
        assert isinstance(result, datetime)
        assert result.hour == 0

    def test_null_passthrough(self):
        assert LlmExtractor._coerce_value(None, "str", "f") is None
        assert LlmExtractor._coerce_value(None, "datetime", "f") is None

    def test_invalid_returns_none(self):
        assert LlmExtractor._coerce_value("not-a-date", "datetime", "f") is None
        assert LlmExtractor._coerce_value("abc", "int", "f") is None


class TestValidateConfig:
    def test_valid_placeholders(self):
        cfg = LlmExtractorConfig(prompt_template="Extract from: {text}")
        inputs = [{"name": "text"}]
        errors = LlmExtractor.validate_config(cfg, inputs, [])
        assert errors == []

    def test_unknown_placeholder(self):
        cfg = LlmExtractorConfig(prompt_template="Extract {text} and {missing}")
        inputs = [{"name": "text"}]
        errors = LlmExtractor.validate_config(cfg, inputs, [])
        assert len(errors) == 1
        assert "missing" in errors[0]

    def test_no_placeholders(self):
        cfg = LlmExtractorConfig(prompt_template="Just extract everything")
        errors = LlmExtractor.validate_config(cfg, [], [])
        assert errors == []


class TestLlmExtractorWithMock:
    """Test the full run() flow with a mocked OpenAI client."""

    def _mock_openai_response(self, response_json: dict):
        """Create a mock that patches OpenAI to return the given JSON."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_json)

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_basic_extraction(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "location_name": "American Airlines Center",
            "address": "2500 Victory Ave, Dallas, TX 75219",
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmExtractor,
            config={"prompt_template": "Extract from: {text}"},
            inputs={"text": "Name: AMERICAN AIRLINES CENTER\nAdd: 2500 Victory Ave"},
            output_pins={"location_name": "str", "address": "str"},
        )

        assert result["location_name"] == "American Airlines Center"
        assert result["address"] == "2500 Victory Ave, Dallas, TX 75219"

        # Verify the API was called
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["temperature"] == 0.0

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_datetime_output(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "start_time": "2026-04-05T23:00:00",
            "end_time": "2026-04-05T23:00:00",
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmExtractor,
            config={"prompt_template": "Extract times from: {text}"},
            inputs={"text": "04/05/26 @ 23:00 - 23:00"},
            output_pins={"start_time": "datetime", "end_time": "datetime"},
        )

        assert isinstance(result["start_time"], datetime)
        assert result["start_time"].hour == 23
        assert isinstance(result["end_time"], datetime)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_null_handling(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "name": "Test",
            "phone": None,
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmExtractor,
            config={"prompt_template": "Extract from: {text}"},
            inputs={"text": "Name: Test"},
            output_pins={"name": "str", "phone": "str"},
        )

        assert result["name"] == "Test"
        assert result["phone"] is None

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_multiple_inputs(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({"summary": "Combined info"})
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmExtractor,
            config={"prompt_template": "Combine {pickup} and {delivery}"},
            inputs={"pickup": "Dallas TX", "delivery": "Houston TX"},
            output_pins={"summary": "str"},
        )

        assert result["summary"] == "Combined info"

        # Verify both inputs were substituted into the prompt
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        user_msg = call_kwargs["messages"][1]["content"]
        assert "Dallas TX" in user_msg
        assert "Houston TX" in user_msg

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_prompt_includes_output_schema(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({"count": 5})
        mock_openai_cls.return_value = mock_client

        run_module(
            LlmExtractor,
            config={"prompt_template": "Count items in: {text}"},
            inputs={"text": "a, b, c, d, e"},
            output_pins={"count": "int"},
        )

        # Verify system prompt contains the output schema
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        system_msg = call_kwargs["messages"][0]["content"]
        assert '"count"' in system_msg
        assert "integer" in system_msg

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_carrier_mawb_extraction(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "carrier_name": "Forward Air",
            "mawb": "95991053",
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmExtractor,
            config={
                "prompt_template": (
                    "Extract the carrier name and MAWB number from: {text}"
                ),
            },
            inputs={"text": "Forward Air(MAWB:95991053)"},
            output_pins={"carrier_name": "str", "mawb": "str"},
        )

        assert result["carrier_name"] == "Forward Air"
        assert result["mawb"] == "95991053"


# ============================================================================
# Integration Tests (requires OPENAI_API_KEY)
# ============================================================================

needs_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)


@needs_api_key
class TestLlmExtractorIntegration:
    """Tests that hit the real OpenAI API. Skipped unless OPENAI_API_KEY is set."""

    def test_pickup_extraction(self, run_module):
        pickup_text = (
            "Pickup: 04/05/26 @ 23:00 - 23:00\n"
            "  Name:.American AIRLINES CENTER\n"
            "  Add:2500 Victory Ave\n"
            "      Jenny Powelson/NBC COMPOUND\n"
            "     DALLAS TX 75219"
        )

        result = run_module(
            LlmExtractor,
            config={
                "prompt_template": (
                    "The following is pickup information from a logistics order document:\n\n"
                    "{pickup_text}\n\n"
                    "Extract the location name with proper casing, the physical street "
                    "address (street, city, state, zip only — exclude contact names), "
                    "and the pickup start and end date-times."
                ),
            },
            inputs={"pickup_text": pickup_text},
            output_pins={
                "location_name": "str",
                "address": "str",
                "start_time": "datetime",
                "end_time": "datetime",
            },
        )

        # Location name should be cleaned up
        assert "american airlines center" in result["location_name"].lower()

        # Address should have street + city/state/zip, not contact name
        assert "2500" in result["address"]
        assert "Dallas" in result["address"] or "DALLAS" in result["address"]
        assert "Jenny" not in result["address"]
        assert "NBC COMPOUND" not in result["address"]

        # Datetimes should parse correctly
        assert isinstance(result["start_time"], datetime)
        assert isinstance(result["end_time"], datetime)
        assert result["start_time"].hour == 23

    def test_carrier_mawb_extraction(self, run_module):
        result = run_module(
            LlmExtractor,
            config={
                "prompt_template": (
                    "Extract the carrier name and MAWB number from: {text}"
                ),
            },
            inputs={"text": "Forward Air(MAWB:95991053)"},
            output_pins={"carrier_name": "str", "mawb": "str"},
        )

        assert result["carrier_name"] == "Forward Air"
        assert result["mawb"] == "95991053"
