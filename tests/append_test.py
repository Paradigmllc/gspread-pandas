import pandas as pd
import pytest

from gspread_pandas import Spread


class FakeSheet:
    def __init__(self, values):
        self._values = values

    def get_all_values(self):
        return [list(row) for row in self._values]


def make_spread(values):
    """A Spread wired to a stubbed worksheet, so no network is involved."""
    spread = Spread.__new__(Spread)
    spread.sheet = FakeSheet(values)
    return spread


HEADERS = ["Order ID", "Customer", "Total"]
EXISTING = [HEADERS, ["1", "alice", "10"], ["2", "bob", "20"]]


def align(spread, df, include_index=False, start=(1, 1), match_columns=False):
    return spread._align_for_append(df, include_index, start, match_columns)


def test_appends_below_existing_rows():
    spread = make_spread(EXISTING)
    df = pd.DataFrame([[3, "carol", 30]], columns=HEADERS)

    aligned, start, did_align = align(spread, df)

    assert did_align is True
    assert start == (4, 1)
    assert aligned.values.tolist() == [[3, "carol", 30]]


def test_reordered_columns_land_under_the_right_headers():
    spread = make_spread(EXISTING)
    df = pd.DataFrame([["carol", 30, 3]], columns=["Customer", "Total", "Order ID"])

    aligned, _, _ = align(spread, df)

    assert aligned.values.tolist() == [[3, "carol", 30]]


def test_renamed_columns_are_matched_by_similarity():
    spread = make_spread(EXISTING)
    df = pd.DataFrame([[3, "carol", 30]], columns=["order_id", "customer", "total"])

    aligned, _, _ = align(spread, df)

    assert aligned.values.tolist() == [[3, "carol", 30]]


def test_missing_column_is_left_blank():
    spread = make_spread(EXISTING)
    df = pd.DataFrame([[3, 30]], columns=["Order ID", "Total"])

    aligned, _, _ = align(spread, df)

    assert aligned.values.tolist() == [[3, None, 30]]


def test_unknown_column_is_dropped_rather_than_shifting_the_row():
    spread = make_spread(EXISTING)
    df = pd.DataFrame(
        [[3, "carol", 30, "JP"]], columns=HEADERS + ["Shipping Country"]
    )

    aligned, _, _ = align(spread, df)

    assert aligned.values.tolist() == [[3, "carol", 30]]


def test_index_is_matched_like_any_other_column():
    spread = make_spread(EXISTING)
    df = pd.DataFrame([["carol", 30]], columns=["Customer", "Total"])
    df.index = pd.Index([3], name="Order ID")

    aligned, _, _ = align(spread, df, include_index=True)

    assert aligned.values.tolist() == [[3, "carol", 30]]


def test_empty_sheet_is_left_for_the_normal_write_path():
    spread = make_spread([])
    df = pd.DataFrame([[3, "carol", 30]], columns=HEADERS)

    aligned, start, did_align = align(spread, df)

    assert did_align is False
    assert start == (1, 1)
    assert aligned is df


def test_trailing_blank_headers_are_not_columns():
    spread = make_spread([HEADERS + ["", ""], ["1", "alice", "10", "", ""]])
    df = pd.DataFrame([[3, "carol", 30]], columns=HEADERS)

    aligned, _, _ = align(spread, df)

    assert aligned.shape == (1, 3)


def test_start_offset_reads_the_right_header_row():
    spread = make_spread([["report title"], [""] + HEADERS, ["", "1", "alice", "10"]])
    df = pd.DataFrame([[3, "carol", 30]], columns=HEADERS)

    aligned, start, did_align = align(spread, df, start=(2, 2))

    assert did_align is True
    assert start == (4, 2)
    assert aligned.values.tolist() == [[3, "carol", 30]]


def test_append_and_replace_together_is_rejected():
    spread = make_spread(EXISTING)
    df = pd.DataFrame([[3, "carol", 30]], columns=HEADERS)

    with pytest.raises(ValueError, match="append"):
        spread.df_to_sheet(df, append=True, replace=True)
