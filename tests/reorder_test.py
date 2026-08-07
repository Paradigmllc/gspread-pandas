import pytest
from gspread import Worksheet

from gspread_pandas import Spread, util
from gspread_pandas.exceptions import NoWorksheetException


class FakeWorksheet(Worksheet):
    """Subclasses the real Worksheet so identity lookups work, without needing
    a live spreadsheet to construct one."""

    def __init__(self, title, id_):
        self._properties = {"title": title, "sheetId": id_}


class FakeSpreadsheet:
    def __init__(self, sheets):
        self._sheets = sheets
        self.batches = []

    def worksheets(self):
        return self._sheets

    def batch_update(self, body):
        self.batches.append(body)

    def fetch_sheet_metadata(self):
        return {"sheets": [{"properties": {"title": s.title}} for s in self._sheets]}


def make_spread(titles=("first", "second", "third")):
    sheets = [FakeWorksheet(t, i) for i, t in enumerate(titles)]
    spread = Spread.__new__(Spread)
    spread.spread = FakeSpreadsheet(sheets)
    spread.sheet = None
    spread._spread_metadata = None
    return spread


def moves(spread):
    """The (sheet id, target index) pairs sent to the API."""
    requests = spread.spread.batches[0]["requests"]
    return [
        (
            r["update_sheet_properties"]["properties"]["sheet_id"],
            r["update_sheet_properties"]["properties"]["index"],
        )
        for r in requests
    ]


def test_reorder_by_name():
    spread = make_spread()
    spread.reorder_sheets(["third", "first", "second"])
    assert moves(spread) == [(2, 0), (0, 1), (1, 2)]


def test_reorder_by_index():
    spread = make_spread()
    spread.reorder_sheets([2, 0])
    assert moves(spread) == [(2, 0), (0, 1)]


def test_reorder_by_worksheet_object():
    spread = make_spread()
    third = spread.sheets[2]
    spread.reorder_sheets([third])
    assert moves(spread) == [(2, 0)]


def test_naming_a_subset_only_moves_those():
    """Sheets left out keep their positions relative to each other."""
    spread = make_spread()
    spread.reorder_sheets(["third"])
    assert moves(spread) == [(2, 0)]


def test_names_are_matched_case_insensitively():
    spread = make_spread()
    spread.reorder_sheets(["THIRD"])
    assert moves(spread) == [(2, 0)]


def test_unknown_sheet_raises_rather_than_silently_skipping():
    spread = make_spread()
    with pytest.raises(NoWorksheetException, match="nope"):
        spread.reorder_sheets(["nope"])
    assert spread.spread.batches == []


def test_a_sheet_listed_twice_raises():
    """Otherwise the second move would silently undo the first."""
    spread = make_spread()
    with pytest.raises(ValueError, match="twice"):
        spread.reorder_sheets(["first", "first"])
    assert spread.spread.batches == []


def test_empty_order_sends_nothing():
    spread = make_spread()
    spread.reorder_sheets([])
    assert spread.spread.batches == []


def test_reorder_request_shape():
    assert util.create_reorder_request(7, 2) == {
        "update_sheet_properties": {
            "properties": {"sheet_id": 7, "index": 2},
            "fields": "index",
        }
    }


class FakeClient:
    """Records what create() was asked for."""

    def __init__(self):
        self.created = []

    def open(self, spread):
        from gspread.exceptions import SpreadsheetNotFound

        raise SpreadsheetNotFound(spread)

    def create(self, title, folder_id=None):
        self.created.append((title, folder_id))
        return FakeSpreadsheet([FakeWorksheet("Sheet1", 0)])


def make_creating_spread():
    spread = Spread.__new__(Spread)
    spread.client = FakeClient()
    spread.sheet = None
    return spread


def test_create_passes_the_folder_through():
    spread = make_creating_spread()
    spread.open_spread("Usecase", create=True, folder_id="0ABCdef123")
    assert spread.client.created == [("Usecase", "0ABCdef123")]


def test_create_without_a_folder_still_works():
    spread = make_creating_spread()
    spread.open_spread("Usecase", create=True)
    assert spread.client.created == [("Usecase", None)]
