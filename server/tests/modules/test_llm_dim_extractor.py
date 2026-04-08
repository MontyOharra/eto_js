"""
Tests for LLM Dim Extractor module.

Tests are split into:
- Unit tests: mock the OpenAI API, test dim parsing and validation
- Integration tests: hit the real API (skipped unless OPENAI_API_KEY is set)
"""
import json
import os
from unittest.mock import patch, MagicMock

import pytest

from features.modules.definitions.transform.llm_dim_extractor import LlmDimExtractor, LlmDimExtractorConfig


# ============================================================================
# Unit Tests (no API key needed)
# ============================================================================

class TestLlmDimExtractorConfig:
    def test_defaults(self):
        cfg = LlmDimExtractorConfig()
        assert cfg.model == "gpt-4o-mini"
        assert cfg.temperature == 0.0

    def test_custom_model(self):
        cfg = LlmDimExtractorConfig(model="gpt-4o", temperature=0.1)
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.1


class TestLlmDimExtractorWithMock:
    """Test the full run() flow with a mocked OpenAI client."""

    def _mock_openai_response(self, response_json: dict):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_json)

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_single_dim(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "dims": [
                {"length": 48.0, "width": 40.0, "height": 36.0, "qty": 2, "weight": 500.0}
            ]
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmDimExtractor,
            config={},
            inputs={"pcs_text": "2", "dims_text": "48x40x36", "weight_text": "500 lbs"},
            output_pins={"dims": "list[dim]"},
        )

        dims = result["dims"]
        assert len(dims) == 1
        assert dims[0]["length"] == 48.0
        assert dims[0]["width"] == 40.0
        assert dims[0]["height"] == 36.0
        assert dims[0]["qty"] == 2
        assert dims[0]["weight"] == 500.0

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_multiple_dims(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "dims": [
                {"length": 48.0, "width": 40.0, "height": 36.0, "qty": 2, "weight": 400.0},
                {"length": 24.0, "width": 24.0, "height": 24.0, "qty": 1, "weight": 100.0},
            ]
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmDimExtractor,
            config={},
            inputs={
                "pcs_text": "2/1",
                "dims_text": "48x40x36/24x24x24",
                "weight_text": "500 lbs",
            },
            output_pins={"dims": "list[dim]"},
        )

        dims = result["dims"]
        assert len(dims) == 2
        assert dims[0]["qty"] == 2
        assert dims[0]["length"] == 48.0
        assert dims[1]["qty"] == 1
        assert dims[1]["length"] == 24.0

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_empty_input_returns_empty_list(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({"dims": []})
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmDimExtractor,
            config={},
            inputs={"pcs_text": "", "dims_text": "", "weight_text": ""},
            output_pins={"dims": "list[dim]"},
        )

        assert result["dims"] == []

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_weight_distributed(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "dims": [
                {"length": 48.0, "width": 40.0, "height": 36.0, "qty": 2, "weight": 333.333},
                {"length": 24.0, "width": 24.0, "height": 24.0, "qty": 1, "weight": 166.667},
            ]
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmDimExtractor,
            config={},
            inputs={
                "pcs_text": "2/1",
                "dims_text": "48x40x36/24x24x24",
                "weight_text": "500 lbs total",
            },
            output_pins={"dims": "list[dim]"},
        )

        dims = result["dims"]
        assert len(dims) == 2
        assert dims[0]["weight"] == 333.333
        assert dims[1]["weight"] == 166.667

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_values_rounded_to_3_decimals(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({
            "dims": [
                {"length": 48.12345, "width": 40.6789, "height": 36.0, "qty": 1, "weight": 123.45678}
            ]
        })
        mock_openai_cls.return_value = mock_client

        result = run_module(
            LlmDimExtractor,
            config={},
            inputs={"pcs_text": "1", "dims_text": "48x40x36", "weight_text": "123 lbs"},
            output_pins={"dims": "list[dim]"},
        )

        dim = result["dims"][0]
        assert dim["length"] == 48.123
        assert dim["width"] == 40.679
        assert dim["weight"] == 123.457

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_prompt_includes_all_inputs(self, mock_openai_cls, run_module):
        mock_client = self._mock_openai_response({"dims": []})
        mock_openai_cls.return_value = mock_client

        run_module(
            LlmDimExtractor,
            config={},
            inputs={"pcs_text": "3", "dims_text": "50x40x30", "weight_text": "750"},
            output_pins={"dims": "list[dim]"},
        )

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        user_msg = call_kwargs["messages"][1]["content"]
        assert "3" in user_msg
        assert "50x40x30" in user_msg
        assert "750" in user_msg


# ============================================================================
# Integration Tests (requires OPENAI_API_KEY)
# ============================================================================

needs_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set"
)


@needs_api_key
class TestLlmDimExtractorIntegration:
    """Tests that hit the real OpenAI API. Skipped unless OPENAI_API_KEY is set."""

    def test_simple_single_dim(self, run_module):
        result = run_module(
            LlmDimExtractor,
            config={},
            inputs={
                "pcs_text": "2",
                "dims_text": "48x40x36",
                "weight_text": "500 lbs",
            },
            output_pins={"dims": "list[dim]"},
        )

        dims = result["dims"]
        assert len(dims) == 1
        assert dims[0]["qty"] == 2
        assert dims[0]["length"] == 48.0
        assert dims[0]["width"] == 40.0
        assert dims[0]["height"] == 36.0
        assert dims[0]["weight"] == 500.0

    def test_multi_line_dims(self, run_module):
        result = run_module(
            LlmDimExtractor,
            config={},
            inputs={
                "pcs_text": "2/1",
                "dims_text": "48x40x36/24x24x24",
                "weight_text": "500 lbs",
            },
            output_pins={"dims": "list[dim]"},
        )

        dims = result["dims"]
        assert len(dims) == 2
        assert dims[0]["qty"] == 2
        assert dims[0]["length"] == 48.0
        assert dims[1]["qty"] == 1
        assert dims[1]["length"] == 24.0
        # Total weight should sum to 500
        total_weight = sum(d["weight"] for d in dims)
        assert abs(total_weight - 500.0) < 1.0
