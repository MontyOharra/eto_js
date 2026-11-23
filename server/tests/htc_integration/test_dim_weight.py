"""Tests for dim weight calculation when writing dims to HTC."""
import pytest

from features.htc_integration.order_utils import HtcOrderUtils
from shared.exceptions import OutputExecutionError
from shared.types.pending_actions import DimObject


class FakeCursor:
    def __init__(self, branch_row):
        self._branch_row = branch_row
        self.executed: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._branch_row


class FakeConnection:
    def __init__(self, branch_row):
        self.cursor_obj = FakeCursor(branch_row)

    def cursor(self):
        return self.cursor_obj


def make_utils(branch_row):
    connection = FakeConnection(branch_row)
    utils = HtcOrderUtils(lambda: connection, co_id=1, br_id=1)
    return utils, connection.cursor_obj


def inserts(cursor):
    return [params for sql, params in cursor.executed if "INSERT INTO" in sql]


class TestCalculateDimWeight:
    def test_matches_htc_formula(self):
        # HTC VBA: new_Qty * (new_Length * new_Width * new_Height) / DimFactor
        assert HtcOrderUtils.calculate_dim_weight(2, 48, 40, 36, 250) == 2 * (48 * 40 * 36) / 250

    def test_includes_qty(self):
        one = HtcOrderUtils.calculate_dim_weight(1, 10, 10, 10, 250)
        five = HtcOrderUtils.calculate_dim_weight(5, 10, 10, 10, 250)
        assert one == 4.0
        assert five == 20.0

    def test_not_rounded(self):
        assert HtcOrderUtils.calculate_dim_weight(1, 1, 1, 1, 250) == 0.004


class TestCreateDimsRecords:
    def test_uses_branch_dim_factor(self):
        utils, cursor = make_utils((250.0,))
        dims = [DimObject(length=48, width=40, height=36, qty=2, weight=500)]

        assert utils.create_dims_records(117000, dims) == 1

        select_sql, select_params = cursor.executed[0]
        assert "BrDimFNatlAir" in select_sql
        assert "HTC300_G000_T020 Branch Info" in select_sql
        assert select_params == (1, 1)
        assert inserts(cursor)[0][-1] == 552.96

    def test_follows_factor_changes_in_htc(self):
        utils, cursor = make_utils((200.0,))
        dims = [DimObject(length=10, width=10, height=10, qty=1, weight=5)]

        utils.create_dims_records(117000, dims)

        assert inserts(cursor)[0][-1] == 5.0

    def test_no_dims_skips_lookup(self):
        utils, cursor = make_utils((250.0,))

        assert utils.create_dims_records(117000, []) == 0
        assert cursor.executed == []

    @pytest.mark.parametrize("branch_row", [None, (None,), (0,)])
    def test_missing_or_invalid_factor_fails_loudly(self, branch_row):
        utils, cursor = make_utils(branch_row)
        dims = [DimObject(length=10, width=10, height=10, qty=1, weight=5)]

        with pytest.raises(OutputExecutionError):
            utils.create_dims_records(117000, dims)

        assert inserts(cursor) == []
