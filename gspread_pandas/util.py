import warnings
from re import match
from time import sleep

import numpy as np
import pandas as pd
from google.oauth2 import credentials as oauth2, service_account
from gspread.exceptions import APIError
from gspread.utils import a1_to_rowcol, rowcol_to_a1

from gspread_pandas.exceptions import MissMatchException

ROW = START = 0
COL = END = 1
DEPRECATION_WARNINGS_ENABLED = True
_WARNINGS_ALREADY_ENABLED = False

# assuming no one will be 10 levels deep
auto_generated_index_names = ["level_{}".format(i) for i in range(10)] + ["index"]


def decode(strg):
    try:
        strg = strg.decode()
    except AttributeError:
        pass
    return strg


def parse_sheet_index(df, index):
    """Parse sheet index into df index."""
    if index and len(df.columns) >= index:
        df = df.set_index(df.columns[index - 1])
        # if column was MultiIndex, the name is a tuple;
        # choose last non-empty value in tuple
        # since that is more common
        if type(df.index.name) == tuple:
            df.index.name = [x for x in df.index.name if x][-1]
        # get rid of falsey index names
        df.index.name = df.index.name or None
    return df


def parse_df_col_names(df, include_index, index_size=1, flatten_sep=None):
    """Parse column names from a df into sheet headers."""
    headers = df.columns.tolist()

    # handle multi-index headers
    if len(headers) > 0 and type(headers[0]) == tuple:

        if isinstance(flatten_sep, str):
            headers = [
                [
                    # Remove blank elements and join using sep
                    flatten_sep.join([ele for ele in header if ele != ""])
                    for header in headers
                ]
            ]
        else:
            headers = [list(row) for row in zip(*headers)]

        # Pandas sets index name as top level col name when using reset_index;
        # move the index name to bottom level since that reads more natural
        if include_index:
            for i in range(index_size):
                top = headers[0]
                bottom = headers[-1]

                # Pandas sets the index's column name as "index" if it doesn't have a
                # name so we need to clean that up
                bottom[i] = top[i] if top[i] not in auto_generated_index_names else ""

                if len(headers) > 1:
                    top[i] = ""

    # handle regular columns
    else:
        headers = [headers]

    return headers


def parse_sheet_headers(vals, header_rows):
    """Parse headers from a sheet into df columns."""
    col_names = None
    if header_rows:
        headers = vals[:header_rows]
        if len(headers) > 0:
            if header_rows > 1:
                _fix_sheet_header_level(headers)
                col_names = pd.MultiIndex.from_arrays(headers)
            elif header_rows == 1:
                col_names = pd.Index(headers[0])

    return col_names


def _fix_sheet_header_level(header_names):
    for col_ix in range(len(header_names[0])):
        _shift_header_up(header_names, col_ix)

    return header_names


def _shift_header_up(
    header_names, col_index, row_index=0, shift_val=0, found_first=False
):
    """Recursively shift headers up so that top level is not empty."""
    rows = len(header_names)
    if row_index < rows:
        current_value = header_names[row_index][col_index]

        if current_value == "" and not found_first:
            shift_val += 1
        else:
            found_first = True

        shift_val = _shift_header_up(
            header_names, col_index, row_index + 1, shift_val, found_first
        )
        if shift_val <= row_index:
            header_names[row_index - shift_val][col_index] = current_value

        if row_index + shift_val >= rows:
            header_names[row_index][col_index] = ""
    return shift_val


def set_col_names(df, col_names):
    """Set the column names on the DataFrame and ensure the set even if there's no
    data."""
    if col_names is not None:
        if len(df.columns) == len(col_names):
            df.columns = col_names
        elif len(df) == 0:
            # if we have headers but no data, set column headers on empty DF
            df = df.reindex(columns=col_names)
        else:
            raise MissMatchException(
                "Column headers don't match number of data columns"
            )
    return df


def chunks(lst, chunk_size):
    """Chunk a list into specified chunk sizes."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def deprecate(message):
    """Display message about deprecation."""
    global _WARNINGS_ALREADY_ENABLED
    # force enable DeprecationWarnings since most interactive shells have
    # them disabled
    if DEPRECATION_WARNINGS_ENABLED and not _WARNINGS_ALREADY_ENABLED:
        _WARNINGS_ALREADY_ENABLED = True
        warnings.filterwarnings(
            "default", ".*", category=DeprecationWarning, module="gspread_pandas"
        )
    # provide ability to disable them at runtime
    if _WARNINGS_ALREADY_ENABLED and not DEPRECATION_WARNINGS_ENABLED:
        warnings.filterwarnings(
            "ignore", ".*", category=DeprecationWarning, module="gspread_pandas"
        )

    warnings.warn(message, DeprecationWarning, stacklevel=2)


def create_filter_request(sheet_id, start, end):
    """Create v4 API request to create a filter for a given worksheet."""
    start = get_cell_as_tuple(start)
    end = get_cell_as_tuple(end)

    return {
        "setBasicFilter": {
            "filter": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start[ROW],
                    "endRowIndex": end[ROW],
                    "startColumnIndex": start[COL],
                    "endColumnIndex": end[COL],
                }
            }
        }
    }


def create_frozen_request(sheet_id, rows=None, cols=None):
    """Create v4 API request to freeze rows and/or columns for a given worksheet."""
    grid_properties = {}

    if rows is not None and rows >= 0:
        grid_properties["frozen_row_count"] = rows

    if cols is not None and cols >= 0:
        grid_properties["frozen_column_count"] = cols

    changed_props = grid_properties.keys()

    return {
        "update_sheet_properties": {
            "properties": {"sheet_id": sheet_id, "grid_properties": grid_properties},
            "fields": "grid_properties({0})".format(", ".join(changed_props)),
        }
    }


def fillna(df, fill_value=""):
    """
    Replace null values with `fill_value`.

    Also replaces in categorical columns.
    """
    for col in df.dtypes[df.dtypes == "category"].index:
        if fill_value not in df[col].cat.categories:
            df[col] = df[col].cat.add_categories([fill_value])
    return df.fillna(fill_value)


def get_cell_as_tuple(cell):
    """Take cell in either format, validate, and return as tuple."""
    if type(cell) == tuple:
        if (
            len(cell) != 2
            or not np.issubdtype(type(cell[ROW]), np.integer)
            or not np.issubdtype(type(cell[COL]), np.integer)
        ):
            raise TypeError("{0} is not a valid cell tuple".format(cell))
        return cell
    elif isinstance(cell, str):
        if not match("[a-zA-Z]+[0-9]+", cell):
            raise TypeError("{0} is not a valid address".format(cell))
        return a1_to_rowcol(cell)
    else:
        raise TypeError("{0} is not a valid format".format(cell))


def get_range(start, end):
    """Transform start and end to cell range like A1:B5."""
    start_int = get_cell_as_tuple(start)
    end_int = get_cell_as_tuple(end)

    return "{0}:{1}".format(rowcol_to_a1(*start_int), rowcol_to_a1(*end_int))


def create_merge_cells_request(sheet_id, start, end, merge_type="MERGE_ALL"):
    """Create v4 API request to merge rows and/or columns for a given worksheet."""
    start = get_cell_as_tuple(start)
    end = get_cell_as_tuple(end)

    return {
        "mergeCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start[ROW] - 1,
                "endRowIndex": end[ROW],
                "startColumnIndex": start[COL] - 1,
                "endColumnIndex": end[COL],
            },
            "mergeType": merge_type,
        }
    }


def create_unmerge_cells_request(sheet_id, start, end):
    """Create v4 API request to unmerge rows and/or columns for a given worksheet."""
    start = get_cell_as_tuple(start)
    end = get_cell_as_tuple(end)

    return {
        "unmergeCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start[ROW] - 1,
                "endRowIndex": end[ROW],
                "startColumnIndex": start[COL] - 1,
                "endColumnIndex": end[COL],
            }
        }
    }


def monkey_patch_request(client, retry_delay=10):
    """Monkey patch gspread's HTTPClient.request to auto-retry with a delay when you
    get a 100 seconds RESOURCE_EXCHAUSTED error."""
    http_client = client.http_client
    original_request = http_client.request

    def request(*args, **kwargs):
        try:
            return original_request(*args, **kwargs)
        except APIError as e:
            # gspread 6 drops the status field from APIError.__str__, so read the
            # structured error instead of matching against the string
            error = getattr(e, "error", None) or {}
            message = error.get("message", "")
            # Only retry on 100 seconds quota breaches
            if error.get("status") == "RESOURCE_EXHAUSTED" and (
                "100" in message or "Read requests" in message
            ):
                sleep(retry_delay)
                return request(*args, **kwargs)
            raise

    http_client.request = request


def create_merge_headers_request(sheet_id, headers, start, index_size):
    """Create v4 API request to merge header labels for a given worksheet."""
    request = []
    start = get_cell_as_tuple(start)

    if isinstance(headers, pd.MultiIndex):
        merge_cells = get_merge_ranges(headers)
        request.append(
            [
                create_merge_cells_request(
                    sheet_id,
                    (start[ROW] + row_ix, col_rng[START] + start[COL] + index_size),
                    (start[ROW] + row_ix, col_rng[END] + start[COL] + index_size),
                )
                for row_ix, row in enumerate(merge_cells)
                for col_rng in row
            ]
        )

    return request


def create_merge_index_request(sheet_id, index, start, header_size):
    """Create v4 API request to merge index labels for a given worksheet."""
    request = []
    start = get_cell_as_tuple(start)

    if isinstance(index, pd.MultiIndex):
        merge_cells = get_merge_ranges(index)
        request.append(
            [
                create_merge_cells_request(
                    sheet_id,
                    (start[ROW] + row_rng[START] + header_size, start[COL] + col_ix),
                    (start[ROW] + row_rng[END] + header_size, start[COL] + col_ix),
                )
                for col_ix, col in enumerate(merge_cells)
                for row_rng in col
            ]
        )

    return request


def get_merge_ranges(index):
    """
    Get list of ranges to be merged for each level of columns.

    For each level, same values will only be merged if they share the
    same label for the level above.
    """
    labels = index.codes if hasattr(index, "codes") else index.labels
    # Dummy range indicating the full size, this is removed at the end
    ranges = [[(0, len(labels[0]))]]

    for ix, index_level in enumerate(labels[:]):
        index_ranges = []
        for rng in ranges[ix]:
            index_ranges.extend(
                get_contiguous_ranges(index_level, rng[START], rng[END])
            )
        ranges.append(index_ranges)

    ranges.pop(0)
    return ranges


def get_contiguous_ranges(lst, lst_start, lst_end):
    """
    Get list of tuples, each indicating the range of contiguous equal values in the lst
    between lst_start and lst_end. Everything is 0 indexed.

    For example, get_contiguous_ranges([0, 0, 0, 1, 1], 1, 4) = [(0, 2), (3, 4)]
    [(the 2nd and 3rd items are both 0), (the 4th and 5th items are both 1)]
    """
    prev_val = None
    index_ranges = []
    lst_section = lst[lst_start : lst_end + 1]
    rng_start = lst_section[START]

    for ix, val in enumerate(lst_section):
        # If there's more than 1 value in the range and there's a change in val
        if rng_start < ix - 1 and prev_val != val:
            # Save the rng until the previous val
            index_ranges.append((lst_start + rng_start, lst_start + ix - 1))
        # If this is the last val and the val is still the same
        elif ix == len(lst_section) - 1 and prev_val == val:
            # Save the rng including the last val
            index_ranges.append((lst_start + rng_start, lst_start + ix))

        if prev_val != val:
            rng_start = ix

        prev_val = val
    return index_ranges


def convert_credentials(credentials):
    """Convert oauth2client credentials to google-auth."""
    cls = credentials.__class__.__name__

    if cls == "ServiceAccountCredentials":
        return _convert_service_account(credentials)
    elif cls == "OAuth2Credentials" or cls == "GoogleCredentials":
        return _convert_oauth(credentials)

    raise TypeError(
        "Credentials need to be from either oauth2client or from google-auth."
    )


def _convert_oauth(credentials):
    return oauth2.Credentials(
        credentials.access_token,
        credentials.refresh_token,
        credentials.id_token,
        credentials.token_uri,
        credentials.client_id,
        credentials.client_secret,
        credentials.scopes,
    )


def _convert_service_account(credentials):
    data = credentials.serialization_data
    data["token_uri"] = credentials.token_uri
    scopes = credentials._scopes.split() or [
        "https://www.googleapis.com/auth/drive",
        "https://spreadsheets.google.com/feeds",
    ]

    return service_account.Credentials.from_service_account_info(data, scopes=scopes)


def parse_permission(perm):
    """Convert the string permission into a dict to unpack for insert_permission."""
    perm_dict = {}
    perm = perm.split("|")
    for part in perm:
        if "@" in part:
            perm_dict["value"] = part
            perm_dict["perm_type"] = "user"
        elif "." in part:
            perm_dict["value"] = part
            perm_dict["perm_type"] = "domain"
        elif "anyone" == part:
            perm_dict["perm_type"] = "anyone"
        elif part in ["grp", "group"]:
            perm_dict["perm_type"] = "group"
        elif part in ["owner", "writer", "reader"]:
            perm_dict["role"] = part
        elif part in ["no", "false"]:
            perm_dict["notify"] = False
        elif part == "link":
            perm_dict["with_link"] = True
        perm_dict["role"] = perm_dict.get("role", "reader")
    return perm_dict


def remove_keys(dct, keys=[]):
    """Remove keys from a dict."""
    return {key: val for key, val in dct.items() if key not in keys}


def remove_keys_from_list(lst, keys=[]):
    """Remove keys from a list of dicts."""
    return [remove_keys(ele, keys) for ele in lst]


def add_paths(root, dirs):
    """
    Recursively build a `path` property to each dir.

    Pass in the root dir and a list of all available dirs.
    """
    # TODO: handle scenario with folders having more than one parent
    children = [dr for dr in dirs if root.get("id", None) in dr.get("parents", [])]
    path = root.get("path", root.get("name", ""))

    for child in children:
        child["path"] = (path + "/" + child["name"]).replace("//", "/")

        add_paths(child, dirs)


def folders_to_create(search_path, dirs, base_path=""):
    """
    Recursively traverse through folder paths looking for the longest existing subpath.

    Return the dir info of the longest subpath and the directories that
    need to be created.
    """
    # Allow user to pass in a string, but use a list in the recursion
    if isinstance(search_path, list):
        parts = search_path
    else:
        parts = search_path.strip("/").split("/")

    # shared drives don't start with a /
    if base_path == "" and not search_path.startswith("/"):
        base_path = parts.pop(0)

    parent = [dr for dr in dirs if dr.get("path", "") == base_path]
    if len(parent) == 0:
        parent = {"id": "root"}
    else:
        parent = parent.pop()

    # Stop if we ran out of parts to create
    if len(parts) == 0:
        return parent, []

    base_path += "/" + parts[0]

    dirs = [dr for dr in dirs if dr.get("path", "").startswith(base_path)]

    # If there's base_path matches, then keep looking for a longer path
    if len(dirs) > 0:
        return folders_to_create(parts[1:], dirs, base_path)
    else:
        return parent, parts


def get_ranges(sheet_name, cols):
    """Get a list of ranges for the given worksheet and columns."""
    ranges = []
    for col in cols:
        start_label = rowcol_to_a1(1, col)
        range_label = "%s!%s:%s" % (sheet_name, start_label, start_label[:-1])
        ranges.append(range_label)
    return ranges


def is_int(val):
    return isinstance(val, (int, np.integer))


def expand_all_columns(cols, width):
    """
    Turn the ``-1`` shorthand into every column position.

    ``-1`` rather than a word like "all", because these arguments accept column
    names as well as numbers, and any word could be somebody's column name.
    Column numbers are 1-based, so -1 can't be one.
    """
    if is_int(cols):
        cols = [cols]

    if list(cols) == [-1]:
        return list(range(1, width + 1))

    return cols


def is_indexes(lst):
    """Is this a list of indexes (all ints)"""
    return all([is_int(val) for val in lst])


def find_col_indexes(cols, col_names, col_offset=1):
    """Given a column name Index, find the numeric indeces of the columns in the
    spreadsheet."""
    col_locs = []

    for col in cols:
        loc = col_names.get_loc(col)
        if is_int(loc):
            col_locs.append(loc)
        elif isinstance(loc, slice):
            col_locs += list(range(len(col_names))[loc])
        elif isinstance(loc, np.ndarray):
            col_locs += [ix for ix in range(len(loc)) if loc[ix]]
    # add 1 because we want the index based on spreadsheet, not python
    return [ele + col_offset for ele in set(col_locs)]


def axis_is_index(axis):
    return axis in ("index", 0)


def axis_is_column(axis):
    return axis in ("columns", 1)
