import pandas as pd
import pytest

from gspread_pandas import clean


def frame(**columns):
    return pd.DataFrame(columns)


def test_integers_become_integers():
    df = clean.convert_types(frame(qty=["1", "2", "3"]), use_ai=False)
    assert df["qty"].tolist() == [1, 2, 3]
    assert str(df["qty"].dtype) == "Int64"


def test_thousands_separators_and_currency_are_stripped():
    df = clean.convert_types(frame(total=["$1,234", "$5,678"]), use_ai=False)
    assert df["total"].tolist() == [1234, 5678]


def test_decimals_stay_floats():
    df = clean.convert_types(frame(rate=["1.5", "2.0"]), use_ai=False)
    assert df["rate"].tolist() == [1.5, 2.0]
    assert df["rate"].dtype == float


def test_textual_booleans_become_booleans():
    df = clean.convert_types(frame(paid=["yes", "no", "YES"]), use_ai=False)
    assert df["paid"].tolist() == [True, False, True]


def test_dates_become_datetimes():
    df = clean.convert_types(frame(day=["2026-01-02", "2026-03-04"]), use_ai=False)
    assert df["day"].dt.year.tolist() == [2026, 2026]


def test_bare_years_stay_integers():
    df = clean.convert_types(frame(year=["2026", "2025"]), use_ai=False)
    assert df["year"].tolist() == [2026, 2025]


def test_one_bad_value_leaves_the_whole_column_alone():
    df = clean.convert_types(frame(qty=["1", "2", "N/A"]), use_ai=False)
    assert df["qty"].tolist() == ["1", "2", "N/A"]


def test_blanks_are_ignored_not_treated_as_failures():
    df = clean.convert_types(frame(qty=["1", "", "3"]), use_ai=False)
    assert df["qty"].tolist()[0] == 1
    assert pd.isna(df["qty"].tolist()[1])


def test_empty_column_is_left_alone():
    df = clean.convert_types(frame(nothing=["", ""]), use_ai=False)
    assert df["nothing"].tolist() == ["", ""]


def test_percentages_are_left_as_text():
    # Stripping "%" would turn 50% into 50 and move the decimal point.
    df = clean.convert_types(frame(share=["50%", "25%"]), use_ai=False)
    assert df["share"].tolist() == ["50%", "25%"]


def test_mixed_words_stay_strings():
    df = clean.convert_types(frame(name=["alice", "bob"]), use_ai=False)
    assert df["name"].tolist() == ["alice", "bob"]


def test_other_columns_are_untouched():
    original = frame(qty=["1", "2"], name=["a", "b"])
    df = clean.convert_types(original, use_ai=False)
    assert df["name"].tolist() == ["a", "b"]
    assert original["qty"].tolist() == ["1", "2"], "input frame was mutated"


class TestAITypes:
    def _patch(self, monkeypatch, response):
        monkeypatch.setattr(clean.ai, "ask_json", lambda *a, **k: response)

    def test_ai_can_widen_what_is_recognised(self, monkeypatch):
        self._patch(monkeypatch, {"types": {"flag": "boolean"}})
        df = clean.convert_types(frame(flag=["T", "F"]), use_ai=True)
        assert df["flag"].tolist() == [True, False]

    def test_proposal_that_does_not_convert_is_dropped(self, monkeypatch):
        self._patch(monkeypatch, {"types": {"name": "integer"}})
        df = clean.convert_types(frame(name=["alice", "bob"]), use_ai=True)
        assert df["name"].tolist() == ["alice", "bob"]

    def test_unknown_type_name_is_ignored(self, monkeypatch):
        self._patch(monkeypatch, {"types": {"name": "rm -rf"}})
        df = clean.convert_types(frame(name=["alice"]), use_ai=True)
        assert df["name"].tolist() == ["alice"]

    def test_unknown_column_is_ignored(self, monkeypatch):
        self._patch(monkeypatch, {"types": {"not_here": "integer"}})
        df = clean.convert_types(frame(name=["alice"]), use_ai=True)
        assert df["name"].tolist() == ["alice"]

    @pytest.mark.parametrize("response", [None, {}, {"types": "nope"}])
    def test_junk_response_falls_back(self, monkeypatch, response):
        self._patch(monkeypatch, response)
        df = clean.convert_types(frame(qty=["1", "2"]), use_ai=True)
        assert df["qty"].tolist() == [1, 2]

    def test_ai_is_not_called_when_everything_is_already_typed(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            clean.ai, "ask_json", lambda *a, **k: calls.append(1) or None
        )
        clean.convert_types(frame(qty=["1", "2"]), use_ai=True)
        assert calls == []
