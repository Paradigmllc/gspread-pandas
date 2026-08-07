"""
Column matching for appending a DataFrame to a sheet that already has headers.

Real sheets drift: a column gets renamed between exports, someone reorders
them, a new one shows up mid-quarter. Appending positionally silently writes
values under the wrong header, so every append resolves names instead.

Matching runs in three passes, cheapest first, and each pass only sees what the
previous one could not place:

1. exact match once case, whitespace and punctuation are normalized
2. the configured model, if :data:`GSPREAD_PANDAS_AI_API_KEY` is set
3. difflib similarity

The model is asked for a name-to-name mapping and nothing else, and anything it
returns that is not a pair of names actually present is discarded, so a wrong or
hostile answer can only ever fail to match a column.
"""

from difflib import SequenceMatcher

from gspread_pandas import ai

__all__ = ["match_columns", "normalize_name"]

# Below this, difflib pairings are noise -- "date" and "rate" score 0.75.
SIMILARITY_CUTOFF = 0.8

_INSTRUCTIONS = (
    "You are aligning the columns of a pandas DataFrame with the header row of "
    "an existing spreadsheet so rows can be appended under the right headers. "
    "Match on meaning, allowing for renames, abbreviations, translations and "
    "formatting differences. Reply with "
    '{"mapping": {"<dataframe column>": "<sheet header or null>"}}. '
    "Use null when a DataFrame column has no counterpart. Never invent names: "
    "every key must come from dataframe_columns and every value must come from "
    "sheet_headers."
)


def normalize_name(name):
    """Fold a column name down to its comparable core."""
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def match_columns(df_columns, sheet_headers, sample_rows=None, use_ai=None):
    """
    Map DataFrame columns onto existing sheet headers.

    Parameters
    ----------
    df_columns : list
        column names from the DataFrame being appended
    sheet_headers : list
        header values already in the worksheet
    sample_rows : list
        optional, a few rows of DataFrame values to help the model
        disambiguate columns whose names alone are unclear
    use_ai : bool
        optional, force the model on or off; by default it is used whenever
        :data:`GSPREAD_PANDAS_AI_API_KEY` is set (default None)

    Returns
    -------
    dict
        every DataFrame column mapped to a sheet header, or to None when it
        has no counterpart
    """
    df_columns = list(df_columns)
    sheet_headers = list(sheet_headers)

    mapping = {}
    available = list(sheet_headers)

    by_normalized = {}
    for header in available:
        by_normalized.setdefault(normalize_name(header), header)

    for column in df_columns:
        header = by_normalized.get(normalize_name(column))
        if header is not None and header in available:
            mapping[column] = header
            available.remove(header)

    unmatched = [column for column in df_columns if column not in mapping]

    if unmatched and available:
        if use_ai is None:
            use_ai = ai.is_enabled()
        if use_ai:
            mapping.update(_match_with_ai(unmatched, available, sample_rows, mapping))
            unmatched = [column for column in df_columns if column not in mapping]
            available = [
                header for header in available if header not in mapping.values()
            ]

    for column in unmatched:
        mapping[column] = _closest(column, available)
        if mapping[column] is not None:
            available.remove(mapping[column])

    return {column: mapping[column] for column in df_columns}


def _closest(column, available):
    """Best difflib match for a column, or None if nothing is close enough."""
    target = normalize_name(column)
    best, best_score = None, SIMILARITY_CUTOFF

    for header in available:
        score = SequenceMatcher(None, target, normalize_name(header)).ratio()
        if score >= best_score:
            best, best_score = header, score

    return best


def _match_with_ai(unmatched, available, sample_rows, already_mapped):
    """Ask the model to pair up the leftovers, discarding anything invented."""
    response = ai.ask_json(
        _INSTRUCTIONS,
        {
            "dataframe_columns": [str(column) for column in unmatched],
            "sheet_headers": [str(header) for header in available],
            "dataframe_sample": ai.sample_rows(sample_rows or []),
        },
    )
    if not response:
        return {}

    proposed = response.get("mapping")
    if not isinstance(proposed, dict):
        return {}

    # The model only ever sees names as strings, so match its answers back onto
    # the real objects -- a column may well be a tuple or an int.
    columns_by_str = {str(column): column for column in unmatched}
    headers_by_str = {str(header): header for header in available}

    confirmed = {}
    taken = set()
    for key, value in proposed.items():
        column = columns_by_str.get(str(key))
        header = headers_by_str.get(str(value))
        if column is None or header is None:
            continue
        if column in confirmed or header in taken or header in already_mapped.values():
            continue
        confirmed[column] = header
        taken.add(header)

    return confirmed
