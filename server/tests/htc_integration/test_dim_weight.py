"""Tests for dim weight calculation when writing dims to HTC."""
from features.htc_integration.order_utils import HtcOrderUtils
from shared.types.pending_actions import DimObject


class FakeCursor:
    def __init__(self):
        self.executed: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self.executed.append((sql, params))


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self):
        return self.cursor_obj


class TestCalculateDimWeight:
    def test_matches_htc_formula(self):
        # HTC VBA: new_Qty * (new_Length * new_Width * new_Height) / 250
        assert HtcOrderUtils.calculate_dim_weight(2, 48, 40, 36) == 2 * (48 * 40 * 36) / 250

    def test_includes_qty(self):
        assert HtcOrderUtils.calculate_dim_weight(1, 10, 10, 10) == 4.0
        assert HtcOrderUtils.calculate_dim_weight(5, 10, 10, 10) == 20.0

    def test_not_rounded(self):
        assert HtcOrderUtils.calculate_dim_weight(1, 1, 1, 1) == 0.004


class TestCreateDimsRecords:
    def test_writes_htc_dim_weight(self):
        connection = FakeConnection()
        utils = HtcOrderUtils(lambda: connection, co_id=1, br_id=1)
        dims = [DimObject(length=48, width=40, height=36, qty=2, weight=500)]

        assert utils.create_dims_records(117000, dims) == 1

        executed = connection.cursor_obj.executed
        assert len(executed) == 1
        sql, params = executed[0]
        assert "INSERT INTO [HTC300_G040_T012A Open Order Dims]" in sql
        assert params[-1] == 552.96
