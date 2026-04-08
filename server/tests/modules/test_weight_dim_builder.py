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

    def test_zero_weight_returns_none(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": 2, "weight": 0},
            output_pins={"dim": "dim"},
        )

        assert result["dim"] is None

    def test_default_count_is_1(self, run_module):
        result = run_module(
            WeightDimBuilder,
            config={},
            inputs={"count": None, "weight": 100.0},
            output_pins={"dim": "dim"},
        )

        assert result["dim"]["qty"] == 1
        assert result["dim"]["weight"] == 100.0
