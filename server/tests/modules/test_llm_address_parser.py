"""Tests for LLM Address Parser module."""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from features.modules.definitions.transform.llm_address_parser import (
    LlmAddressParser,
    LlmAddressParserConfig,
    SYSTEM_PROMPT,
    _supports_temperature,
)


OUTPUT_PINS = {"company_name": "str", "address": "str", "parse_success": "bool"}


class TestLlmAddressParserConfig:
    def test_defaults(self):
        cfg = LlmAddressParserConfig()
        assert cfg.model == "gpt-5-mini"
        assert cfg.temperature == 0.0
        assert cfg.additional_instructions == ""

    def test_custom_instructions(self):
        cfg = LlmAddressParserConfig(
            additional_instructions="the warehouse name appears below the street"
        )
        assert cfg.additional_instructions == "the warehouse name appears below the street"


class TestTemperatureSupport:
    @pytest.mark.parametrize("model", ["gpt-5-mini", "gpt-5", "gpt-5-nano", "o1-mini", "o3", "o4-mini"])
    def test_reasoning_models_omit_temperature(self, model):
        assert _supports_temperature(model) is False

    @pytest.mark.parametrize("model", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"])
    def test_chat_models_accept_temperature(self, model):
        assert _supports_temperature(model) is True


class TestLlmAddressParserWithMock:
    def _mock_openai_response(self, response_json: dict):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_json)
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_extracts_company_and_address(self, mock_openai_cls, run_module):
        mock_openai_cls.return_value = self._mock_openai_response({
            "company_name": "Acme Corp",
            "address": "1234 Main St Ste 400, Dallas, TX 75201",
        })

        result = run_module(
            LlmAddressParser,
            config={},
            inputs={"text": "ACME CORP 1234 MAIN ST STE 400 ORDER #100000 ATTN JOHN DALLAS TX 75201"},
            output_pins=OUTPUT_PINS,
        )

        # Values are normalized to uppercase to match HTC storage conventions
        assert result["company_name"] == "ACME CORP"
        assert result["address"] == "1234 MAIN ST STE 400, DALLAS, TX 75201"
        assert result["parse_success"] is True

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_null_address_reports_failure(self, mock_openai_cls, run_module):
        mock_openai_cls.return_value = self._mock_openai_response({
            "company_name": "Acme Corp",
            "address": None,
        })

        result = run_module(
            LlmAddressParser,
            config={},
            inputs={"text": "ACME CORP - CALL FOR DIRECTIONS"},
            output_pins=OUTPUT_PINS,
        )

        assert result["company_name"] == "ACME CORP"
        assert result["address"] == ""
        assert result["parse_success"] is False

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_empty_input_skips_llm(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({})
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmAddressParser,
            config={},
            inputs={"text": "   "},
            output_pins=OUTPUT_PINS,
        )

        assert result == {"company_name": "", "address": "", "parse_success": False}
        mock_client.chat.completions.create.assert_not_called()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_omits_temperature_for_default_model(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "company_name": "Acme", "address": "1 Main St, Dallas, TX 75201"
        })
        mock_openai_cls.return_value = mock_client

        run_module(
            LlmAddressParser,
            config={},
            inputs={"text": "ACME 1 MAIN ST DALLAS TX 75201"},
            output_pins=OUTPUT_PINS,
        )

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "gpt-5-mini"
        assert "temperature" not in kwargs

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_sends_temperature_for_chat_model(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "company_name": "Acme", "address": "1 Main St, Dallas, TX 75201"
        })
        mock_openai_cls.return_value = mock_client

        run_module(
            LlmAddressParser,
            config={"model": "gpt-4o-mini", "temperature": 0.0},
            inputs={"text": "ACME 1 MAIN ST DALLAS TX 75201"},
            output_pins=OUTPUT_PINS,
        )

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["temperature"] == 0.0

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_retries_without_temperature_when_rejected(self, mock_openai_cls, run_module):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "company_name": "Acme", "address": "1 Main St, Dallas, TX 75201"
        })
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            Exception("Unsupported value: 'temperature' does not support 0.0"),
            mock_response,
        ]
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmAddressParser,
            config={"model": "gpt-4o-mini"},
            inputs={"text": "ACME 1 MAIN ST DALLAS TX 75201"},
            output_pins=OUTPUT_PINS,
        )

        assert result["parse_success"] is True
        assert mock_client.chat.completions.create.call_count == 2
        assert "temperature" not in mock_client.chat.completions.create.call_args.kwargs

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_additional_instructions_appended(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "company_name": "Acme", "address": "1 Main St, Dallas, TX 75201"
        })
        mock_openai_cls.return_value = mock_client

        run_module(
            LlmAddressParser,
            config={"additional_instructions": "the dock number follows the street"},
            inputs={"text": "ACME 1 MAIN ST DALLAS TX 75201"},
            output_pins=OUTPUT_PINS,
        )

        system_message = mock_client.chat.completions.create.call_args.kwargs["messages"][0]
        assert system_message["content"].startswith(SYSTEM_PROMPT)
        assert "the dock number follows the street" in system_message["content"]

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_invalid_json_raises(self, mock_openai_cls, run_module):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not json"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        with pytest.raises(ValueError, match="invalid JSON"):
            run_module(
                LlmAddressParser,
                config={},
                inputs={"text": "ACME 1 MAIN ST DALLAS TX 75201"},
                output_pins=OUTPUT_PINS,
            )

    @patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False)
    @patch("openai.OpenAI")
    def test_missing_api_key_raises(self, mock_openai_cls, run_module):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            run_module(
                LlmAddressParser,
                config={},
                inputs={"text": "ACME 1 MAIN ST DALLAS TX 75201"},
                output_pins=OUTPUT_PINS,
            )
