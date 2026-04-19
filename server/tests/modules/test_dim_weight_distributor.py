"""Tests for Dim Weight Distributor module."""
from features.modules.definitions.transform.dim_weight_distributor import (
    DimWeightDistributor,
)


class TestDimWeightDistributorByPieceCount:
    def test_equal_distribution(self, run_module):
        dims = [
            {"length": 48, "width": 40, "height": 40, "qty": 1, "weight": 0},
            {"length": 48, "width": 40, "height": 46, "qty": 1, "weight": 0},
        ]
        result = run_module(
            DimWeightDistributor,
            config={"method": "by_piece_count"},
            inputs={"dims": dims, "total_weight": 500.0},
            output_pins={"dims": "list[dim]"},
        )

        out = result["dims"]
        assert len(out) == 2
        assert out[0]["weight"] == 250.0
        assert out[1]["weight"] == 250.0

    def test_proportional_by_qty(self, run_module):
        dims = [
            {"length": 48, "width": 40, "height": 40, "qty": 2, "weight": 0},
            {"length": 48, "width": 40, "height": 46, "qty": 4, "weight": 0},
        ]
        result = run_module(
            DimWeightDistributor,
            config={"method": "by_piece_count"},
            inputs={"dims": dims, "total_weight": 600.0},
            output_pins={"dims": "list[dim]"},
        )

        out = result["dims"]
        # 2/6 * 600 = 200, 4/6 * 600 = 400
        assert out[0]["weight"] == 200.0
        assert out[1]["weight"] == 400.0

    def test_passthrough_when_weights_exist(self, run_module):
        dims = [
            {"length": 48, "width": 40, "height": 40, "qty": 2, "weight": 300},
            {"length": 48, "width": 40, "height": 46, "qty": 4, "weight": 700},
        ]
        result = run_module(
            DimWeightDistributor,
            config={},
            inputs={"dims": dims, "total_weight": 999.0},
            output_pins={"dims": "list[dim]"},
        )

        out = result["dims"]
        # Should not redistribute — weights already present
        assert out[0]["weight"] == 300
        assert out[1]["weight"] == 700

    def test_passthrough_when_total_weight_zero(self, run_module):
        dims = [
            {"length": 48, "width": 40, "height": 40, "qty": 1, "weight": 0},
        ]
        result = run_module(
            DimWeightDistributor,
            config={},
            inputs={"dims": dims, "total_weight": 0},
            output_pins={"dims": "list[dim]"},
        )

        assert result["dims"][0]["weight"] == 0

    def test_empty_list(self, run_module):
        result = run_module(
            DimWeightDistributor,
            config={},
            inputs={"dims": [], "total_weight": 500.0},
            output_pins={"dims": "list[dim]"},
        )

        assert result["dims"] == []

    def test_string_weight_input(self, run_module):
        dims = [
            {"length": 48, "width": 40, "height": 40, "qty": 1, "weight": 0},
        ]
        result = run_module(
            DimWeightDistributor,
            config={},
            inputs={"dims": dims, "total_weight": "500"},
            output_pins={"dims": "list[dim]"},
        )

        assert result["dims"][0]["weight"] == 500.0


class TestDimWeightDistributorByVolume:
    def test_proportional_by_volume(self, run_module):
        dims = [
            {"length": 10, "width": 10, "height": 10, "qty": 1, "weight": 0},  # vol = 1000
            {"length": 20, "width": 10, "height": 10, "qty": 1, "weight": 0},  # vol = 2000
        ]
        result = run_module(
            DimWeightDistributor,
            config={"method": "by_volume"},
            inputs={"dims": dims, "total_weight": 300.0},
            output_pins={"dims": "list[dim]"},
        )

        out = result["dims"]
        # 1000/3000 * 300 = 100, 2000/3000 * 300 = 200
        assert out[0]["weight"] == 100.0
        assert out[1]["weight"] == 200.0

    def test_volume_with_qty(self, run_module):
        dims = [
            {"length": 10, "width": 10, "height": 10, "qty": 2, "weight": 0},  # total vol = 2000
            {"length": 10, "width": 10, "height": 10, "qty": 1, "weight": 0},  # total vol = 1000
        ]
        result = run_module(
            DimWeightDistributor,
            config={"method": "by_volume"},
            inputs={"dims": dims, "total_weight": 300.0},
            output_pins={"dims": "list[dim]"},
        )

        out = result["dims"]
        assert out[0]["weight"] == 200.0
        assert out[1]["weight"] == 100.0

    def test_zero_volume_falls_back_to_piece_count(self, run_module):
        dims = [
            {"length": 0, "width": 0, "height": 0, "qty": 1, "weight": 0},
            {"length": 0, "width": 0, "height": 0, "qty": 3, "weight": 0},
        ]
        result = run_module(
            DimWeightDistributor,
            config={"method": "by_volume"},
            inputs={"dims": dims, "total_weight": 400.0},
            output_pins={"dims": "list[dim]"},
        )

        out = result["dims"]
        # Falls back to piece count: 1/4 * 400 = 100, 3/4 * 400 = 300
        assert out[0]["weight"] == 100.0
        assert out[1]["weight"] == 300.0
