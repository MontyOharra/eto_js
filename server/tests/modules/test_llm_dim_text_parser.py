"""Tests for LLM Dim Text Parser module."""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from features.modules.definitions.transform.llm_dim_text_parser import (
    LlmDimTextParser,
    LlmDimTextParserConfig,
)


class TestLlmDimTextParserConfig:
    def test_defaults(self):
        cfg = LlmDimTextParserConfig()
        assert cfg.model == "gpt-4o-mini"
        assert cfg.temperature == 0.0
        assert cfg.description == ""

    def test_custom_description(self):
        cfg = LlmDimTextParserConfig(description="dims are in cm")
        assert cfg.description == "dims are in cm"


class TestLlmDimTextParserWithMock:
    def _mock_openai_response(self, response_json: dict):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_json)
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_standard_dims(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "dims": [
                {"length": 48, "width": 40, "height": 40, "qty": 2, "weight": 0},
                {"length": 48, "width": 40, "height": 46, "qty": 4, "weight": 0},
            ]
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmDimTextParser,
            config={},
            inputs={"text": "48x40x40 (2), 48x40x46 (4)"},
            output_pins={"dims": "list[dim]"},
        )

        dims = result["dims"]
        assert len(dims) == 2
        assert dims[0]["qty"] == 2
        assert dims[0]["length"] == 48
        assert dims[0]["weight"] == 0
        assert dims[1]["qty"] == 4
        assert dims[1]["height"] == 46

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_with_weights(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "dims": [
                {"length": 48, "width": 40, "height": 40, "qty": 2, "weight": 500},
            ]
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmDimTextParser,
            config={},
            inputs={"text": "48x40x40 (2) 500lbs"},
            output_pins={"dims": "list[dim]"},
        )

        assert result["dims"][0]["weight"] == 500

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_empty_input(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({"dims": []})
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmDimTextParser,
            config={},
            inputs={"text": ""},
            output_pins={"dims": "list[dim]"},
        )

        assert result["dims"] == []

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_description_appended_to_prompt(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({"dims": []})
        mock_openai_cls.return_value = mock_client

        run_module(
            LlmDimTextParser,
            config={"description": "dims are in cm, convert to inches"},
            inputs={"text": "100x50x50"},
            output_pins={"dims": "list[dim]"},
        )

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        system_msg = call_kwargs["messages"][0]["content"]
        assert "dims are in cm, convert to inches" in system_msg


needs_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)


@needs_api_key
class TestLlmDimTextParserIntegration:
    def test_standard_format(self, run_module):
        result = run_module(
            LlmDimTextParser,
            config={},
            inputs={"text": "48x40x40 (2), 48x40x46 (4)"},
            output_pins={"dims": "list[dim]"},
        )

        dims = result["dims"]
        assert len(dims) == 2
        assert dims[0]["qty"] == 2
        assert dims[0]["length"] == 48
        assert dims[0]["width"] == 40
        assert dims[0]["height"] == 40
        assert dims[0]["weight"] == 0
        assert dims[1]["qty"] == 4
