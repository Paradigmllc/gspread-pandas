import pytest

from gspread_pandas import smart

CLEAN = [["Order ID", "Total"], ["1", "10"]]
WITH_PREAMBLE = [
    ["Q3 revenue report"],
    [],
    ["Order ID", "Total"],
    ["1", "10"],
]


def test_clean_sheet_starts_at_row_one():
    assert smart.detect_structure(CLEAN, use_ai=False) == {
        "start_row": 1,
        "header_rows": 1,
    }


def test_title_and_blank_rows_are_skipped():
    assert smart.detect_structure(WITH_PREAMBLE, use_ai=False) == {
        "start_row": 3,
        "header_rows": 1,
    }


def test_ragged_preamble_rows_are_skipped():
    values = [["exported 2026-08-01"], ["", ""], ["ID", "Name"], ["1", "a"]]
    assert smart.detect_structure(values, use_ai=False)["start_row"] == 3


def test_empty_sheet_falls_back_to_defaults():
    assert smart.detect_structure([], use_ai=False) == {
        "start_row": 1,
        "header_rows": 1,
    }


def test_single_column_sheet_falls_back_to_defaults():
    assert smart.detect_structure([["only"], ["a"]], use_ai=False)["start_row"] == 1


class TestAIStructure:
    def _patch(self, monkeypatch, response):
        monkeypatch.setattr(smart.ai, "ask_json", lambda *a, **k: response)

    def test_ai_can_find_stacked_headers(self, monkeypatch):
        self._patch(monkeypatch, {"start_row": 3, "header_rows": 2})
        values = WITH_PREAMBLE + [["2", "20"]]
        assert smart.detect_structure(values, use_ai=True) == {
            "start_row": 3,
            "header_rows": 2,
        }

    @pytest.mark.parametrize(
        "response",
        [
            {"start_row": 0, "header_rows": 1},
            {"start_row": 1, "header_rows": 0},
            {"start_row": 99, "header_rows": 1},
            {"start_row": 1, "header_rows": 99},
            {"start_row": "third", "header_rows": 1},
            {"header_rows": 1},
            None,
        ],
    )
    def test_impossible_answers_fall_back_to_the_heuristic(self, monkeypatch, response):
        self._patch(monkeypatch, response)
        assert smart.detect_structure(WITH_PREAMBLE, use_ai=True) == {
            "start_row": 3,
            "header_rows": 1,
        }
