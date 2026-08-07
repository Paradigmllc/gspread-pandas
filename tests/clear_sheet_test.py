import pytest

from gspread_pandas import Spread


class FakeSheet:
    title = "sheet"

    def __init__(self):
        self.resizes = []

    def resize(self, rows, cols):
        self.resizes.append((rows, cols))


class FakeSpreadsheet:
    def __init__(self, sheet):
        self._sheet = sheet

    def worksheets(self):
        return [self._sheet]


def make_spread(frozen_rows=0, frozen_cols=0):
    """A Spread whose worksheet reports the given frozen counts."""
    spread = Spread.__new__(Spread)
    spread.sheet = FakeSheet()
    spread.spread = FakeSpreadsheet(spread.sheet)
    spread.updates = []
    spread.update_cells = lambda start, end, vals, **kw: spread.updates.append(
        (start, end, len(vals), set(vals))
    )
    spread._spread_metadata = {
        "sheets": [
            {
                "properties": {
                    "title": "sheet",
                    "gridProperties": {
                        "frozenRowCount": frozen_rows,
                        "frozenColumnCount": frozen_cols,
                    },
                }
            }
        ]
    }
    return spread


def cleared_range(spread):
    (start, end, count, values) = spread.updates[0]
    assert values == {""}, "cleared cells must be written blank"
    return start, end, count


def test_plain_sheet_clears_only_the_surviving_cell():
    spread = make_spread()
    spread.clear_sheet()
    assert cleared_range(spread) == ((1, 1), (1, 1), 1)


def test_frozen_rows_are_cleared_not_left_behind():
    """A sheet can't shrink past its frozen rows, so they survive the resize
    and used to keep their values -- only A1 was cleared (#97)."""
    spread = make_spread(frozen_rows=2)
    spread.clear_sheet()
    assert cleared_range(spread) == ((1, 1), (3, 1), 3)


def test_frozen_columns_are_cleared_too():
    spread = make_spread(frozen_cols=3)
    spread.clear_sheet()
    assert cleared_range(spread) == ((1, 1), (1, 4), 4)


def test_frozen_rows_and_columns_clear_the_whole_block():
    spread = make_spread(frozen_rows=2, frozen_cols=1)
    spread.clear_sheet()
    assert cleared_range(spread) == ((1, 1), (3, 2), 6)


def test_the_shrink_matches_what_is_cleared():
    """Whatever the sheet shrinks to is exactly what has to be cleared by hand."""
    spread = make_spread(frozen_rows=2, frozen_cols=1)
    spread.clear_sheet()
    shrink_to = spread.sheet.resizes[0]
    _, end, _ = cleared_range(spread)
    assert shrink_to == end


@pytest.mark.parametrize("rows,cols", [(1, 1), (10, 5), (2, 2)])
def test_requested_size_is_honoured(rows, cols):
    spread = make_spread(frozen_rows=2, frozen_cols=1)
    spread.clear_sheet(rows, cols)
    assert spread.sheet.resizes[-1] == (max(rows, 3), max(cols, 2))
