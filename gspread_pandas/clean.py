"""
Giving sheet values their real types.

Everything comes back from the Sheets API as a string, so a freshly pulled
DataFrame is all ``object`` columns and no arithmetic, sorting or date filtering
works until the caller converts by hand.

Inference is deliberately strict: a column is only converted when *every*
non-empty value in it converts cleanly. A column that is 99% numbers and 1%
"N/A" stays as strings rather than quietly turning that 1% into nulls, because
silent data loss during a read is much worse than an unconverted column.

The model, when :data:`GSPREAD_PANDAS_AI_API_KEY` is set, only gets to *propose*
a type per column, drawn from :data:`TYPES`. Its proposal is then run through
exactly the same strict conversion as everything else, and dropped if it doesn't
hold, so it can widen what gets recognised but can never force a bad cast.
"""

import pandas as pd

from gspread_pandas import ai

__all__ = ["convert_types", "infer_types", "apply_types", "TYPES"]

#: Types a column can be converted to. The model may only choose from these.
TYPES = ("integer", "float", "boolean", "datetime", "string")

TRUE_VALUES = {"true", "yes", "y", "t"}
FALSE_VALUES = {"false", "no", "n", "f"}

# Stripped before a numeric test. Currency symbols and thousands separators
# don't change a value's meaning; "%" is left alone, since dropping it would
# turn 50% into 50 and silently move a decimal point.
NUMERIC_NOISE = str.maketrans("", "", "$€£¥₩,   ")

_INSTRUCTIONS = (
    "You are assigning a type to each column of a table pulled out of a "
    "spreadsheet, where every value arrived as text. Judge from the column "
    "name and the sample values. Reply with "
    '{"types": {"<column>": "<type>"}}, where type is one of: '
    + ", ".join(TYPES)
    + ". Use string when unsure. Every key must be a column that was given."
)


def convert_types(df, use_ai=None):
    """
    Convert a DataFrame of strings to the types its values actually hold.

    Parameters
    ----------
    df : DataFrame
        the frame to convert, typically straight from a worksheet
    use_ai : bool
        optional, force the model on or off; by default it is used whenever
        :data:`GSPREAD_PANDAS_AI_API_KEY` is set (default None)

    Returns
    -------
    DataFrame
        a new frame, with converted columns where conversion was unambiguous
    """
    return apply_types(df, infer_types(df, use_ai=use_ai))


def infer_types(df, use_ai=None):
    """
    Work out what type each column holds.

    Returns
    -------
    dict
        column name to one of :data:`TYPES`
    """
    types = {column: _infer_column(df[column]) for column in df.columns}

    undecided = [column for column, kind in types.items() if kind == "string"]
    if not undecided:
        return types

    if use_ai is None:
        use_ai = ai.is_enabled()
    if use_ai:
        types.update(_infer_with_ai(df, undecided))

    return types


def apply_types(df, types):
    """
    Convert columns according to ``types``, leaving anything that won't convert
    cleanly alone.
    """
    converted = df.copy()

    for column, kind in types.items():
        if column not in converted.columns or kind == "string":
            continue
        values = _convert_column(converted[column], kind)
        if values is not None:
            converted[column] = values

    return converted


def _infer_column(series):
    """Narrowest type that every non-empty value in the column satisfies."""
    for kind in ("integer", "float", "boolean", "datetime"):
        if _convert_column(series, kind) is not None:
            return kind

    return "string"


def _convert_column(series, kind):
    """Convert a column, or None if any non-empty value refuses to convert."""
    filled = series[_non_empty(series)]
    if filled.empty:
        return None

    try:
        converted = _CONVERTERS[kind](filled)
    except (TypeError, ValueError, OverflowError):
        return None

    if converted is None or converted.isna().any():
        return None

    return converted.reindex(series.index)


def _non_empty(series):
    return series.notna() & (series.astype(str).str.strip() != "")


def _to_number(filled):
    return pd.to_numeric(filled.astype(str).str.translate(NUMERIC_NOISE))


def _to_integer(filled):
    numbers = _to_number(filled)
    # A float column that happens to hold round numbers is still a float; only
    # call it an integer when nothing was written with a decimal point.
    if filled.astype(str).str.contains(r"[.eE]").any():
        return None
    return numbers.astype("Int64")


def _to_float(filled):
    return _to_number(filled).astype(float)


def _to_boolean(filled):
    lowered = filled.astype(str).str.strip().str.lower()
    if not lowered.isin(TRUE_VALUES | FALSE_VALUES).all():
        return None
    return lowered.isin(TRUE_VALUES).astype("boolean")


def _to_datetime(filled):
    text = filled.astype(str).str.strip()
    # Bare numbers are years, ids and quantities far more often than dates, and
    # to_datetime would happily read "2026" as a timestamp.
    if not text.str.contains(r"[-/:\s]").all():
        return None
    return pd.to_datetime(text, errors="coerce", format="mixed")


_CONVERTERS = {
    "integer": _to_integer,
    "float": _to_float,
    "boolean": _to_boolean,
    "datetime": _to_datetime,
}


def _infer_with_ai(df, undecided):
    """Ask the model about the columns strict inference left as strings."""
    response = ai.ask_json(
        _INSTRUCTIONS,
        {
            "columns": [str(column) for column in undecided],
            "samples": {
                str(column): [
                    str(value)[:60] for value in df[column].head(ai.SAMPLE_ROWS)
                ]
                for column in undecided
            },
        },
    )
    if not response:
        return {}

    proposed = response.get("types")
    if not isinstance(proposed, dict):
        return {}

    by_str = {str(column): column for column in undecided}

    confirmed = {}
    for key, kind in proposed.items():
        column = by_str.get(str(key))
        if column is None or kind not in TYPES or kind == "string":
            continue
        # The model gets a say in what to try, never in what succeeds.
        if _convert_column(df[column], kind) is not None:
            confirmed[column] = kind

    return confirmed
