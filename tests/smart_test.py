import pytest

from gspread_pandas import smart


def test_normalize_name():
    assert smart.normalize_name("Order ID") == smart.normalize_name("order_id")
    assert smart.normalize_name(" Total $ ") == "total"
    assert smart.normalize_name(42) == "42"


def test_exact_match_wins_over_similarity():
    mapping = smart.match_columns(["date", "rate"], ["Rate", "Date"], use_ai=False)
    assert mapping == {"date": "Date", "rate": "Rate"}


def test_reordered_and_renamed_columns():
    mapping = smart.match_columns(
        ["order_id", "Customer Name"],
        ["Customer name", "Order ID"],
        use_ai=False,
    )
    assert mapping == {"order_id": "Order ID", "Customer Name": "Customer name"}


def test_new_column_maps_to_none():
    mapping = smart.match_columns(["total", "discount"], ["Total"], use_ai=False)
    assert mapping == {"total": "Total", "discount": None}


def test_headers_are_never_reused():
    mapping = smart.match_columns(["total", "totals"], ["Total"], use_ai=False)
    assert sorted(mapping) == ["total", "totals"]
    assert list(mapping.values()).count("Total") == 1


def test_difflib_catches_near_miss():
    mapping = smart.match_columns(["quantiy"], ["Quantity"], use_ai=False)
    assert mapping == {"quantiy": "Quantity"}


def test_unrelated_names_do_not_match():
    mapping = smart.match_columns(["shipping_country"], ["Revenue"], use_ai=False)
    assert mapping == {"shipping_country": None}


def test_non_string_columns_survive(monkeypatch):
    mapping = smart.match_columns([("a", "b"), 1], ["1", "('a', 'b')"], use_ai=False)
    assert mapping[1] == "1"
    assert mapping[("a", "b")] == "('a', 'b')"


class TestAIMatching:
    def _patch(self, monkeypatch, response):
        monkeypatch.setattr(smart.ai, "ask_json", lambda *a, **k: response)

    def test_ai_maps_what_difflib_cannot(self, monkeypatch):
        self._patch(monkeypatch, {"mapping": {"revenue": "Sales Total"}})
        mapping = smart.match_columns(["revenue"], ["Sales Total"], use_ai=True)
        assert mapping == {"revenue": "Sales Total"}

    def test_invented_header_is_discarded(self, monkeypatch):
        self._patch(monkeypatch, {"mapping": {"revenue": "Column That Is Not There"}})
        mapping = smart.match_columns(["revenue"], ["Sales Total"], use_ai=True)
        assert mapping == {"revenue": None}

    def test_invented_column_is_discarded(self, monkeypatch):
        self._patch(monkeypatch, {"mapping": {"not_a_column": "Sales Total"}})
        mapping = smart.match_columns(["revenue"], ["Sales Total"], use_ai=True)
        assert mapping == {"revenue": None}

    def test_duplicate_targets_are_discarded(self, monkeypatch):
        self._patch(
            monkeypatch, {"mapping": {"rev": "Sales Total", "inc": "Sales Total"}}
        )
        mapping = smart.match_columns(["rev", "inc"], ["Sales Total"], use_ai=True)
        assert list(mapping.values()).count("Sales Total") == 1

    def test_ai_cannot_steal_an_exact_match(self, monkeypatch):
        self._patch(monkeypatch, {"mapping": {"extra": "Total"}})
        mapping = smart.match_columns(["total", "extra"], ["Total"], use_ai=True)
        assert mapping["total"] == "Total"
        assert mapping["extra"] is None

    @pytest.mark.parametrize("response", [None, {}, {"mapping": "nope"}, {"x": 1}])
    def test_junk_response_falls_back(self, monkeypatch, response):
        self._patch(monkeypatch, response)
        mapping = smart.match_columns(["quantiy"], ["Quantity"], use_ai=True)
        assert mapping == {"quantiy": "Quantity"}
