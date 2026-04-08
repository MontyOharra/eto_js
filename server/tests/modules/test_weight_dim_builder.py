"""Tests for Weight Dim Builder module."""
from features.modules.definitions.transform.weight_dim_builder import WeightDimBuilder


class TestWeightDimBuilder:
    def test_basic(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": 3, "weight": 500.0},
            output_pins={"dim": "dim"},
        )

        dim = result["dim"]
        assert dim["qty"] == 3
        assert dim["weight"] == 500.0
        assert dim["length"] == 1
        assert dim["width"] == 1
        assert dim["height"] == 1

    def test_string_inputs(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": "3", "weight": "500.0"},
            output_pins={"dim": "dim"},
        )

        dim = result["dim"]
        assert dim["qty"] == 3
        assert dim["weight"] == 500.0

    def test_zero_weight_returns_none(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": 2, "weight": 0},
            output_pins={"dim": "dim"},
        )

        assert result["dim"] is None

    def test_zero_count_returns_none(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": 0, "weight": 500.0},
            output_pins={"dim": "dim"},
        )

        assert result["dim"] is None

    def test_empty_string_weight_returns_none(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": "2", "weight": ""},
            output_pins={"dim": "dim"},
        )

        assert result["dim"] is None

    def test_empty_string_count_returns_none(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": "", "weight": "500"},
            output_pins={"dim": "dim"},
        )

        assert result["dim"] is None

    def test_none_inputs_returns_none(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": None, "weight": None},
            output_pins={"dim": "dim"},
        )

        assert result["dim"] is None

    def test_whitespace_only_returns_none(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": "  ", "weight": "  "},
            output_pins={"dim": "dim"},
        )

        assert result["dim"] is None
