import warnings

import pytest

from gspread_pandas import Spread


class FakeSheet:
    title = "sheet"

    def __init__(self, values):
        self._values = values

    def get_all_values(self):
        return [list(row) for row in self._values]


class FakeSpread:
    def __init__(self, sheet):
        self._sheet = sheet

    def worksheets(self):
        return [self._sheet]


def read(values, **kwargs):
    spread = Spread.__new__(Spread)
    spread.sheet = FakeSheet(values)
    spread.spread = FakeSpread(spread.sheet)
    spread._spread_metadata = {"sheets": [{"properties": {"title": "sheet"}}]}
    return spread.sheet_to_df(**kwargs)


@pytest.mark.parametrize(
    "values",
    [
        pytest.param([["a", ""], ["b", ""]], id="column of blanks"),
        pytest.param([["", ""], ["", ""]], id="everything blank"),
        pytest.param([["a", "1"], ["", ""], ["b", "2"]], id="blank row"),
        pytest.param([["a", "1"], ["b"]], id="ragged rows"),
    ],
)
def test_reading_a_sheet_warns_about_nothing(values):
    """A column of blanks used to become all-NaN and get silently downcast off
    object dtype, which pandas 2.2 deprecated (#102)."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        read([["one", "two"]] + values)


def test_blank_rows_are_dropped():
    df = read([["one", "two"], ["a", "1"], ["", ""], ["b", "2"]], index=0)
    assert df.values.tolist() == [["a", "1"], ["b", "2"]]


def test_blank_rows_are_kept_when_asked():
    df = read([["one", "two"], ["a", "1"], ["", ""]], index=0, dropna=False)
    assert df.values.tolist() == [["a", "1"], ["", ""]]


def test_ragged_rows_are_padded_with_blanks():
    df = read([["one", "two"], ["a", "1"], ["b"]], index=0)
    assert df.values.tolist() == [["a", "1"], ["b", ""]]


def test_values_stay_strings():
    df = read([["one", "two"], ["1", "2"], ["", ""], ["3", "4"]], index=0)
    assert df.dtypes.tolist() == [object, object]
    assert df.values.tolist() == [["1", "2"], ["3", "4"]]


def test_blank_column_survives_as_blanks():
    df = read([["one", "two"], ["a", ""], ["b", ""]], index=0)
    assert df["two"].tolist() == ["", ""]
