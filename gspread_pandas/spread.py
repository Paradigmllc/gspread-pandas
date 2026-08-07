from builtins import range, str
from re import match

import pandas as pd
from gspread import Spreadsheet, Worksheet
from gspread.exceptions import (
    APIError,
    NoValidUrlKeyFound,
    SpreadsheetNotFound,
    WorksheetNotFound,
)
from gspread.utils import ValueInputOption, ValueRenderOption, fill_gaps, rightpad

from gspread_pandas.clean import convert_types as convert_column_types
from gspread_pandas.client import Client
from gspread_pandas.conf import default_scope
from gspread_pandas.exceptions import (
    GspreadPandasException,
    MissMatchException,
    NoWorksheetException,
)
from gspread_pandas.smart import (
    detect_structure,
    match_columns as match_columns_to_headers,
)
from gspread_pandas.util import (
    COL,
    ROW,
    axis_is_column,
    axis_is_index,
    chunks,
    create_filter_request,
    create_frozen_request,
    create_merge_cells_request,
    create_merge_headers_request,
    create_merge_index_request,
    create_reorder_request,
    create_unmerge_cells_request,
    expand_all_columns,
    fillna,
    find_col_indexes,
    get_cell_as_tuple,
    get_range,
    get_ranges,
    is_indexes,
    parse_df_col_names,
    parse_permission,
    parse_sheet_headers,
    parse_sheet_index,
    set_col_names,
)

__all__ = ["Spread"]


class Spread:
    """
    Simple wrapper for gspread to interact with Pandas. It holds an instance of an
    'open' spreadsheet, an 'open' worksheet, and a list of available worksheets.

    Each user will be associated with specific OAuth credentials. The authenticated user
    will need the appropriate permissions to the Spreadsheet in order to interact with
    it.

    Parameters
    ----------
    spread : str
        name, url, or id of the spreadsheet; must have read access by
        the authenticated user,
        see :meth:`open_spread <gspread_pandas.spread.Spread.open_spread>`
    sheet : str,int
        optional, name or index of Worksheet,
        see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
        (default 0)
    config : dict
        optional, if you want to provide an alternate configuration,
        see :meth:`get_config <gspread_pandas.conf.get_config>` (default None)
    create_sheet : bool
        whether to create the worksheet if it doesn't exist,
        it wil use the ``spread`` value as the sheet title (default False)
    create_spread : bool
        whether to create the spreadsheet if it doesn't exist,
        it wil use the ``spread`` value as the sheet title (default False)
    scope : list
        optional, if you'd like to provide your own scope
        (default default_scope)
    user : str
        string indicating the key to a users credentials,
        which will be stored in a file (by default they will be stored in
        ``~/.config/gspread_pandas/creds/<user>`` but can be modified with
        ``creds_dir`` property in config). If using a Service Account, this
        will be ignored. (default "default")
    creds : google.auth.credentials.Credentials
        optional, pass credentials if you have those already (default None)
    client : Client
        optionall, if you've already instanciated a Client, you can just pass
        that and it'll be used instead (default None)
    permissions : list
        a list of strings. See
        :meth:`add_permissions <gspread_pandas.spread.Spread.add_permissions>`
        for the expected format
    folder_id : str
        optional, id of the folder to create the spreadsheet in, used only
        alongside ``create_spread``. A path can't name every folder — one
        shared with you may not appear in your own directory tree at all — so
        an id is the only way to reach some of them. Get one from
        :meth:`find_folders <gspread_pandas.client.Client.find_folders>`
        (default None)
    """

    #: `(gspread.spreadsheet.Spreadsheet)` - Currently open Spreadsheet
    spread: Spreadsheet = None

    #: `(gspread.worksheet.Worksheet)` - Currently open Worksheet
    sheet: Worksheet = None

    #: `(Client)` - Instance of gspread_pandas
    #: :class:`Client <gspread_pandas.client.Client>`
    client = None

    _max_range_chunk_size = 1000000

    # `(dict)` - Spreadsheet metadata
    _spread_metadata = None

    def __init__(
        self,
        spread,
        sheet=0,
        config=None,
        create_spread=False,
        create_sheet=False,
        scope=default_scope,
        user="default",
        creds=None,
        client=None,
        permissions=None,
        folder_id=None,
    ):
        if isinstance(client, Client):
            self.client = client
        else:
            self.client = Client(user, config, scope, creds)

        self.open(spread, sheet, create_sheet, create_spread, folder_id)

        if permissions:
            self.add_permissions(permissions)

    def __repr__(self):
        base = "<gspread_pandas.spread.Spread - '{}'>"
        meta = []
        if self.email:
            meta.append("User: '{}'".format(self.email))
        if self.spread:
            meta.append("Spread: '{}'".format(self.spread.title))
        if self.sheet:
            meta.append("Sheet: '{}'".format(self.sheet.title))
        return base.format(", ".join(meta))

    def __iter__(self):
        for sheet in self.sheets:
            yield sheet

    @property
    def email(self):
        """`(str)` - E-mail for the currently authenticated user"""
        return self.client.email

    @property
    def url(self):
        """`(str)` - Url for this spreadsheet"""
        return "https://docs.google.com/spreadsheets/d/{}".format(self.spread.id)

    @property
    def sheets(self):
        """`(list)` - List of available Worksheets"""
        return self.spread.worksheets()

    def refresh_spread_metadata(self):
        """Refresh spreadsheet metadata."""
        self._spread_metadata = self.spread.fetch_sheet_metadata()

        if self.sheet:
            self.sheet._properties = self._sheet_metadata["properties"]

    @property
    def _sheet_metadata(self):
        """`(dict)` - Metadata for currently open worksheet"""
        if self.sheet:
            ix = self._find_sheet(self.sheet.title)[0]
            return self._spread_metadata["sheets"][ix]

    def open(
        self,
        spread,
        sheet=None,
        create_sheet=False,
        create_spread=False,
        folder_id=None,
    ):
        """
        Open a spreadsheet, and optionally a worksheet. See.

        :meth:`open_spread <gspread_pandas.Spread.open_spread>` and
        :meth:`open_sheet <gspread_pandas.Spread.open_sheet>`.

        Parameters
        ----------
        spread : str
            name, url, or id of Spreadsheet
        sheet : str,int
            name or index of Worksheet (default None)
        create_sheet : bool
            whether to create the worksheet if it doesn't exist,
            it wil use the ``spread`` value as the sheet title (default False)
        create_spread : bool
            whether to create the spreadsheet if it doesn't exist,
            it wil use the ``spread`` value as the sheet title (default False)
        folder_id : str
            optional, id of the folder to create the spreadsheet in,
            see :meth:`open_spread <gspread_pandas.spread.Spread.open_spread>`
            (default None)

        Returns
        -------
        None
        """
        self.open_spread(spread, create_spread, folder_id)

        if sheet is not None:
            self.open_sheet(sheet, create_sheet)

    def open_spread(self, spread, create=False, folder_id=None):
        """
        Open a spreadsheet. Authorized user must already have read access.

        Parameters
        ----------
        spread : str
            name, url, or id of Spreadsheet
        create : bool
            whether to create the spreadsheet if it doesn't exist,
            it wil use the ``spread`` value as the sheet title (default False)
        folder_id : str
            optional, id of the folder to create the spreadsheet in. Only
            applies when the spreadsheet is created; opening an existing one
            ignores it. Get an id from
            :meth:`find_folders <gspread_pandas.client.Client.find_folders>`
            (default None)

        Returns
        -------
        None
        """
        id_regex = "[a-zA-Z0-9-_]{44}"
        url_path = "docs.google.com/spreadsheet"

        if match(id_regex, spread):
            open_func = self.client.open_by_key
        elif url_path in spread:
            open_func = self.client.open_by_url
        else:
            open_func = self.client.open

        try:
            self.spread = open_func(spread)
            self.refresh_spread_metadata()
        except (SpreadsheetNotFound, NoValidUrlKeyFound, APIError) as error:
            if create:
                try:
                    self.spread = self.client.create(spread, folder_id=folder_id)
                    self.refresh_spread_metadata()
                except Exception as e:
                    msg = "Couldn't create spreadsheet.\n" + str(e)
                    new_error = GspreadPandasException(msg)
            elif isinstance(error, SpreadsheetNotFound) or "NOT_FOUND" in str(error):
                new_error = SpreadsheetNotFound("Spreadsheet not found")
            else:
                new_error = error

        # Raise new exception outside of except block for a python2/3 way to avoid
        # "During handling of the above exception, another exception occurred"
        if "new_error" in locals() and isinstance(new_error, Exception):
            raise new_error

    def open_sheet(self, sheet, create=False):
        """
        Open a worksheet. Optionally, if the sheet doesn't exist then create it first
        (only when ``sheet`` is a str).

        Parameters
        ----------
        sheet : str,int,Worksheet
            name, index, or Worksheet object
        create : bool
            whether to create the sheet if it doesn't exist,
            see :meth:`create_sheet <gspread_pandas.Spread.create_sheet>`
            (default False)

        Returns
        -------
        None
        """
        self.sheet = None
        if isinstance(sheet, int):
            if sheet >= len(self.sheets) or sheet < -1 * len(self.sheets):
                raise WorksheetNotFound("Invalid sheet index {}".format(sheet))
            self.sheet = self.sheets[sheet]
        else:
            self.sheet = self.find_sheet(sheet)

        if not self.sheet:
            if create:
                self.create_sheet(sheet)
            else:
                raise WorksheetNotFound("Worksheet not found")

    def create_sheet(self, name, rows=1, cols=1):
        """
        Create a new worksheet with the given number of rows and cols.

        Automatically opens that sheet after it's created.

        Parameters
        ----------
        name : str
            name of new Worksheet
        rows : int
            number of rows (default 1)
        cols : int
            number of columns (default 1)

        Returns
        -------
        None
        """
        self.spread.add_worksheet(name, rows, cols)
        self.refresh_spread_metadata()
        self.open_sheet(name)

    def _get_columns(self, cols, value_render_option=ValueRenderOption.formatted):
        """
        Returns a list of all values in `cols`.

        Empty cells in this list will be rendered as :const:`None`.

        Parameters
        ----------
        cols : list of ints
            Column numbers.
        value_render_option : str
            Determines how values should be rendered in the the output. Possible
            values are "FORMATTED_VALUE", "FORMULA", and "UNFORMATTED_VALUE"
            (Default value = "FORMATTED_VALUE")

        Returns
        -------
        """
        ranges = get_ranges(self.sheet.title, cols)
        data = self.spread.values_batch_get(
            ranges,
            params={
                "valueRenderOption": value_render_option,
                "majorDimension": "COLUMNS",
            },
        )

        try:
            return fill_gaps(
                [col.get("values", [[]])[0] for col in data["valueRanges"]]
            )
        except KeyError:
            return []

    def _fix_value_render(
        self, df, first_data_row, col_names, cols, value_render_option
    ):
        """Replace values for columns that need a different value render option."""
        if not is_indexes(cols):
            cols = find_col_indexes(cols, col_names)

        for ix, col in enumerate(self._get_columns(cols, value_render_option)):
            df.iloc[:, cols[ix] - 1] = rightpad(col[first_data_row:], len(df))

    def sheet_to_df(
        self,
        index=1,
        header_rows=1,
        start_row=1,
        unformatted_columns=None,
        formula_columns=None,
        sheet=None,
        dropna=True,
        detect_layout=False,
        convert_types=False,
    ):
        """
        Pull a worksheet into a DataFrame.

        Parameters
        ----------
        index : int
            col number of index column, 0 or None for no index (default 1)
        header_rows : int
            number of rows that represent headers (default 1)
        start_row : int
            row number for first row of headers or data (default 1)
        unformatted_columns : list
            column numbers or names for columns you'd like to pull in as
            unformatted values, or ``-1`` for every column (default None)
        formula_columns : list
            column numbers or names for columns you'd like to pull in as
            actual formulas, or ``-1`` for every column (default None)
        sheet : str,int
            optional, if you want to open a different sheet first,
            see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
            (default None)
        dropna : bool
            whether to remove rows where everything is null (default True)
        detect_layout : bool
            whether to work out ``start_row`` and ``header_rows`` from the
            sheet instead of using the values passed in, for sheets that open
            with a title or a blank row before the table. Uses the configured
            model when ``GSPREAD_PANDAS_AI_API_KEY`` is set and falls back to
            skipping preamble rows otherwise, see
            :func:`detect_structure <gspread_pandas.smart.detect_structure>`
            (default False)
        convert_types : bool
            whether to give columns their real types instead of leaving
            everything as strings. A column is only converted when every
            non-empty value in it converts cleanly. Uses the configured model
            for columns strict inference can't place when
            ``GSPREAD_PANDAS_AI_API_KEY`` is set, see
            :func:`convert_types <gspread_pandas.clean.convert_types>`
            (default False)

        Returns
        -------
        DataFrame
            DataFrame with the data from the Worksheet
        """
        self._ensure_sheet(sheet)

        vals = self.sheet.get_all_values()

        if detect_layout:
            layout = detect_structure(vals)
            start_row = layout["start_row"]
            header_rows = layout["header_rows"] if header_rows else header_rows

        vals = self._fix_merge_values(vals)[start_row - 1 :]

        col_names = parse_sheet_headers(vals, header_rows)

        df = pd.DataFrame(vals[header_rows or 0 :])

        # drop rows where every cell is blank, by masking rather than by
        # replacing blanks with NaN -- an all-blank column would become
        # all-NaN, which pandas silently downcasts off object dtype (#102)
        if dropna:
            blank = df.isna() | (df == "")
            df = df[~blank.all(axis=1)]

        df = df.fillna("")

        # replace values with a different value render option before we set the
        # index in set_col_names
        if unformatted_columns:
            self._fix_value_render(
                df,
                header_rows + start_row - 1,
                col_names,
                expand_all_columns(unformatted_columns, len(df.columns)),
                ValueRenderOption.unformatted,
            )

        if formula_columns:
            self._fix_value_render(
                df,
                header_rows + start_row - 1,
                col_names,
                expand_all_columns(formula_columns, len(df.columns)),
                ValueRenderOption.formula,
            )

        df = set_col_names(df, col_names)

        if convert_types:
            df = convert_column_types(df)

        return parse_sheet_index(df, index)

    def get_sheet_dims(self, sheet=None):
        """
        Get the dimensions of the currently open Worksheet.

        Parameters
        ----------
        sheet : str,int,Worksheet
            optional, if you want to open a different sheet first,
            see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
            (default None)

        Returns
        -------
        tuple
            a tuple containing (num_rows,num_cols)
        """
        self._ensure_sheet(sheet)
        return (self.sheet.row_count, self.sheet.col_count) if self.sheet else None

    def _get_update_chunks(self, start, end, vals):
        start = get_cell_as_tuple(start)
        end = get_cell_as_tuple(end)

        num_cols = end[COL] - start[COL] + 1
        num_rows = end[ROW] - start[ROW] + 1
        num_cells = num_cols * num_rows

        if num_cells != len(vals):
            raise MissMatchException("Number of values needs to match number of cells")

        chunk_rows = self._max_range_chunk_size // num_cols
        chunk_size = chunk_rows * num_cols

        end_cell = (start[ROW] - 1, 0)

        for val_chunks in chunks(vals, int(chunk_size)):
            start_cell = (end_cell[ROW] + 1, start[COL])
            end_cell = (
                min(start_cell[ROW] + chunk_rows - 1, start[ROW] + num_rows - 1),
                end[COL],
            )
            yield start_cell, end_cell, val_chunks

    def update_cells(self, start, end, vals, sheet=None, raw_columns=None):
        """
        Update the values in a given range. The values should be listed in order from
        left to right across rows.

        Parameters
        ----------
        start : tuple,str
            tuple indicating (row, col) or string like 'A1'
        end : tuple,str
            tuple indicating (row, col) or string like 'Z20'
        vals : list
            array of values to populate
        sheet : str,int,Worksheet
            optional, if you want to open a different sheet first,
            see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
            (default None)
        raw_columns : list, int
            optional, list of column numbers in the google sheet that should be
            interpreted as "RAW" input

        Returns
        -------
        None
        """
        self._ensure_sheet(sheet)

        for start_cell, end_cell, val_chunks in self._get_update_chunks(
            start, end, vals
        ):
            rng = get_range(start_cell, end_cell)

            cells = self.sheet.range(rng)

            if len(val_chunks) != len(cells):
                raise MissMatchException(
                    "Number of chunked values doesn't match number of cells"
                )

            for val, cell in zip(val_chunks, cells):
                cell.value = val

            if raw_columns:
                assert isinstance(
                    raw_columns, list
                ), "raw_columns must be a list of ints"
                raw_cells = [i for i in cells if i.col in raw_columns]
                self.sheet.update_cells(raw_cells, ValueInputOption.raw)
            else:
                raw_cells = []

            user_cells = [i for i in cells if i not in raw_cells]
            if user_cells:
                self.sheet.update_cells(user_cells, ValueInputOption.user_entered)

    def _ensure_sheet(self, sheet):
        if sheet is not None:
            self.open_sheet(sheet, create=True)

        if not self.sheet:
            raise NoWorksheetException("No open worksheet")

    def _find_sheet(self, sheet):
        """
        Find a worksheet and return with index.

        Parameters
        ----------
        sheet : str,Worksheet
            Name or worksheet to find


        Returns
        -------
        tuple
            Tuple like (index, worksheet)
        """
        for ix, worksheet in enumerate(self.sheets):
            if isinstance(sheet, str) and sheet.lower() == worksheet.title.lower():
                return ix, worksheet
            if isinstance(sheet, Worksheet) and sheet.id == worksheet.id:
                return ix, worksheet
        return None, None

    def find_sheet(self, sheet):
        """
        Find a given worksheet by title or by object comparison.

        Parameters
        ----------
        sheet : str,Worksheet
            name of Worksheet or Worksheet object

        Returns
        -------
        Worksheet
            the Worksheet by the given name or None if not found
        """
        return self._find_sheet(sheet)[1]

    def reorder_sheets(self, order):
        """
        Move worksheets into the given order.

        Parameters
        ----------
        order : list
            worksheets, by name, index or ``Worksheet``, in the order you want
            them. Worksheets you leave out keep their positions relative to
            each other and follow the ones you named.

        Returns
        -------
        None
        """
        moving = []
        for sheet in order:
            worksheet = self.sheets[sheet] if isinstance(sheet, int) else None
            worksheet = worksheet or self.find_sheet(sheet)
            if worksheet is None:
                raise NoWorksheetException("Worksheet not found: {}".format(sheet))
            if worksheet.id in [w.id for w in moving]:
                raise ValueError("Worksheet listed twice: {}".format(sheet))
            moving.append(worksheet)

        if not moving:
            return

        # Each move is applied in turn and shifts everything after it, so
        # assigning final positions in order lands every sheet where it belongs
        # without having to work out the intermediate shuffling.
        self.spread.batch_update(
            {
                "requests": [
                    create_reorder_request(worksheet.id, index)
                    for index, worksheet in enumerate(moving)
                ]
            }
        )

        self.refresh_spread_metadata()

    def clear_sheet(self, rows=1, cols=1, sheet=None):
        """
        Reset open worksheet to a blank sheet with given dimensions.

        Parameters
        ----------
        rows : int
            number of rows (default 1)
        cols : int
            number of columns (default 1)
        sheet : str,int,Worksheet
            optional; name, index, or Worksheet,
            see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
            (default None)

        Returns
        -------
        None
        """
        self._ensure_sheet(sheet)

        # TODO: if my merge request goes through, use sheet.frozen_*_count
        frozen_rows = self._sheet_metadata["properties"]["gridProperties"].get(
            "frozenRowCount", 0
        )
        frozen_cols = self._sheet_metadata["properties"]["gridProperties"].get(
            "frozenColumnCount", 0
        )

        row_resize = max(rows, frozen_rows + 1)
        col_resize = max(cols, frozen_cols + 1)

        # Values are cleared by shrinking the sheet, which deletes them, and
        # growing it back. A sheet can't shrink past its frozen rows and
        # columns, though, so that block survives and has to be cleared by hand.
        # https://issuetracker.google.com/issues/213126648
        # TODO: these 2 operations could be done in a single batchUpdate call
        kept_rows = frozen_rows + 1
        kept_cols = frozen_cols + 1

        self.sheet.resize(kept_rows, kept_cols)
        self.sheet.resize(row_resize, col_resize)

        self.update_cells(
            start=(1, 1),
            end=(kept_rows, kept_cols),
            vals=[""] * (kept_rows * kept_cols),
        )

    def delete_sheet(self, sheet):
        """
        Delete a worksheet by title. Returns whether the sheet was deleted or not. If
        current sheet is deleted, the ``sheet`` property will be set to None.

        Parameters
        ----------
        sheet : str,Worksheet
            name or Worksheet

        Returns
        -------
        bool
            True if deleted successfully, else False
        """
        is_current = False

        s = self.find_sheet(sheet)

        if s == self.sheet:
            is_current = True

        if s:
            try:
                self.spread.del_worksheet(s)
                if is_current:
                    self.sheet = None
                return True
            except Exception:
                pass

        self.refresh_spread_metadata()

        return False

    def df_to_sheet(
        self,
        df,
        index=True,
        headers=True,
        start=(1, 1),
        replace=False,
        sheet=None,
        raw_columns=None,
        freeze_index=False,
        freeze_headers=False,
        fill_value="",
        add_filter=False,
        merge_headers=False,
        flatten_headers_sep=None,
        merge_index=False,
        append=False,
        match_columns=None,
    ):
        """
        Save a DataFrame into a worksheet.

        Parameters
        ----------
        df : DataFrame
            the DataFrame to save
        index : bool
            whether to include the index in worksheet (default True)
        headers : bool
            whether to include the headers in the worksheet (default True)
        start : tuple,str
            tuple indicating (row, col) or string like 'A1' for top left
            cell (default (1,1))
        replace : bool
            whether to remove everything in the sheet first (default False)
        sheet : str,int,Worksheet
            optional, if you want to open or create a different sheet
            before saving,
            see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
            (default None)
        raw_columns : list, str
            optional, list of columns from your dataframe that you want
            interpreted as RAW input in google sheets. This can be column
            names or column numbers.
        freeze_index : bool
            whether to freeze the index columns (default False)
        freeze_headers : bool
            whether to freeze the header rows (default False)
        fill_value : str
            value to fill nulls with (default '')
        add_filter : bool
            whether to add a filter to the uploaded sheet (default False)
        merge_headers : bool
            whether to merge cells in the header that have the same value
            (default False)
        flatten_headers_sep : str
            if you want to flatten your multi-headers to a single row,
            you can pass the string that you'd like to use to concatenate
            the levels, for example, ': ' (default None)
        merge_index : bool
            whether to merge cells in the index that have the same value
            (default False)
        append : bool
            whether to add the rows below the data already in the sheet
            instead of overwriting from ``start``. Columns are matched to the
            existing headers by name, so a reordered or renamed DataFrame
            still lands under the right headers. Can't be used with
            ``replace`` (default False)
        match_columns : bool
            optional, when appending, whether to use the configured model to
            resolve column names that don't match exactly. Defaults to using
            it whenever ``GSPREAD_PANDAS_AI_API_KEY`` is set; pass False to
            stay with exact and similarity matching only, see
            :mod:`smart <gspread_pandas.smart>` (default None)

        Returns
        -------
        None
        """
        self._ensure_sheet(sheet)

        start = get_cell_as_tuple(start)

        if append:
            if replace:
                raise ValueError("Can't both append to and replace a sheet")
            df, start, aligned = self._align_for_append(df, index, start, match_columns)
            if aligned:
                index = headers = False

        include_index = index
        header = df.columns
        index = df.index
        index_size = index.nlevels if include_index else 0
        header_size = header.nlevels

        if include_index:
            df = df.reset_index()

        df = fillna(df, fill_value)
        df_list = df.values.tolist()

        if headers:
            header_rows = parse_df_col_names(
                df, include_index, index_size, flatten_headers_sep
            )
            df_list = header_rows + df_list

        if not df_list:
            return

        sheet_rows, sheet_cols = self.get_sheet_dims()
        req_rows = len(df_list) + (start[ROW] - 1)
        req_cols = len(df_list[0]) + (start[COL] - 1) or 1

        end = (req_rows, req_cols)

        if replace:
            # this takes care of resizing
            self.clear_sheet(req_rows, req_cols)
        else:
            # make sure sheet is large enough
            self.sheet.resize(max(sheet_rows, req_rows), max(sheet_cols, req_cols))

        if raw_columns:
            if is_indexes(raw_columns):
                offset = index_size + start[COL] - 1
                raw_columns = [ix + offset for ix in raw_columns]
            else:
                raw_columns = find_col_indexes(
                    raw_columns, header, start[COL] + index_size
                )

        self.update_cells(
            start=start,
            end=end,
            vals=[str(val) for row in df_list for val in row],
            raw_columns=raw_columns,
        )

        self.freeze(
            None if not freeze_headers else header_size + start[ROW] - 1,
            None if not freeze_index else index_size + start[COL] - 1,
        )

        if add_filter:
            self.add_filter(
                (header_size + start[ROW] - 2, start[COL] - 1), (req_rows, req_cols)
            )

        if merge_headers:
            self._merge_index(start, header, index_size, "columns")

        if include_index and merge_index:
            self._merge_index(start, index, header_size, "index")

        self.refresh_spread_metadata()

    def _align_for_append(self, df, include_index, start, match_columns):
        """
        Reshape a DataFrame to sit under the headers already in the worksheet.

        Returns the reshaped frame, the cell to start writing at, and whether
        any alignment happened. A sheet with no header row yet is left alone so
        the caller writes it out normally, headers and all.
        """
        existing = self.sheet.get_all_values()
        header_row = start[ROW] - 1

        sheet_headers = (
            existing[header_row][start[COL] - 1 :]
            if (len(existing) > header_row)
            else []
        )
        while sheet_headers and sheet_headers[-1] == "":
            sheet_headers.pop()

        if not sheet_headers:
            return df, start, False

        if include_index:
            df = df.reset_index()

        mapping = match_columns_to_headers(
            df.columns,
            sheet_headers,
            sample_rows=df.head().astype(str).values.tolist(),
            use_ai=match_columns,
        )
        source = {
            header: column for column, header in mapping.items() if header is not None
        }

        # Numbered columns, because a sheet is free to repeat a header name and
        # positions are all that matter once the values are written out.
        columns = [
            df[source[header]].tolist() if header in source else [None] * len(df)
            for header in sheet_headers
        ]
        aligned = pd.DataFrame(list(zip(*columns)), columns=range(len(sheet_headers)))

        return aligned, (len(existing) + 1, start[COL]), True

    def _merge_index(self, start, index, other_axis_size, axis):
        """
        Make a request to merge cells with the same values for the given index.
        This really only applies to MultiIndex.
        """
        if axis_is_index(axis):
            create_requests = create_merge_index_request
        elif axis_is_column(axis):
            create_requests = create_merge_headers_request
        else:
            raise ValueError("Axis should be 'index' or 'columns'")

        self._unmerge_index(start, index, other_axis_size, axis)

        requests = create_requests(self.sheet.id, index, start, other_axis_size)

        if requests:
            self.spread.batch_update({"requests": requests})

    def _unmerge_index(self, start, index, other_axis_size, axis):
        """
        In order to ensure merged cells still match up for the given
        MultiIndex, we need to first unmerge all the cells
        """
        dims = self.get_sheet_dims()
        if axis_is_index(axis):
            ix_start = (
                start[ROW] + other_axis_size,
                start[COL],
            )
            ix_end = (
                dims[ROW],
                start[COL] + index.nlevels - 1,
            )
        elif axis_is_column(axis):
            ix_start = (
                start[ROW],
                start[COL] + other_axis_size,
            )
            ix_end = (
                start[ROW] + index.nlevels - 1,
                dims[COL],
            )
        self.unmerge_cells(ix_start, ix_end)

    def _fix_merge_values(self, vals):
        """
        Assign the top-left value to all cells in a merged range.

        Parameters
        ----------
        vals : list
            Values returned by
            :meth:`get_all_values() <gspread.worksheet.Worksheet.get_all_values()>_`


        Returns
        -------
        list
            Fixed values
        """
        for merge in self._sheet_metadata.get("merges", []):
            start_row, end_row = merge["startRowIndex"], merge["endRowIndex"]
            start_col, end_col = (merge["startColumnIndex"], merge["endColumnIndex"])

            # ignore merge cells outside the data range
            if start_row < len(vals) and start_col < len(vals[0]):
                orig_val = vals[start_row][start_col]
                for row in vals[start_row:end_row]:
                    row[start_col:end_col] = [
                        orig_val for i in range(start_col, end_col)
                    ]

        return vals

    def freeze(self, rows=None, cols=None, sheet=None):
        """
        Freeze rows and/or columns for the open worksheet.

        Parameters
        ----------
        rows : int
            number of rows to freeze, use 0 to 'unfreeze' (default None)
        cols : int
            number of columns to freeze, use 0 to 'unfreeze' (default None)
        sheet : str,int,Worksheet
            optional, if you want to open or create a
            different sheet before freezing,
            see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
            (default None)

        Returns
        -------
        None
        """
        self._ensure_sheet(sheet)

        if rows is None and cols is None:
            return

        self.spread.batch_update(
            {"requests": create_frozen_request(self.sheet.id, rows, cols)}
        )

        self.refresh_spread_metadata()

    def add_filter(self, start=None, end=None, sheet=None):
        """
        Add filters to data in the open worksheet.

        Parameters
        ----------
        start : tuple,str
            Tuple indicating (row, col) or string like 'A1' (default 'A1')
        end : tuple, str
            Tuple indicating (row, col) or string like 'A1'
            (default last cell in sheet)
        sheet : str,int,Worksheet
            optional, if you want to open or create a
            different sheet before adding the filter,
            see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
            (default None)

        Returns
        -------
        None
        """
        self._ensure_sheet(sheet)

        dims = self.get_sheet_dims()

        self.spread.batch_update(
            {
                "requests": create_filter_request(
                    self.sheet.id, start or (0, 0), end or dims
                )
            }
        )

        self.refresh_spread_metadata()

    def merge_cells(self, start, end, merge_type="MERGE_ALL", sheet=None):
        """
        Merge cells between the start and end cells. Use merge_type if you want to
        change the behavior of the merge.

        Parameters
        ----------
        start : tuple,str
            Tuple indicating (row, col) or string like 'A1'
        end : tuple, str
            Tuple indicating (row, col) or string like 'A1'
        merge_type : str
            One of MERGE_ALL, MERGE_ROWS, or MERGE_COLUMNS (default "MERGE_ALL")
        sheet : str,int,Worksheet
            optional, if you want to open or create a
            different sheet before adding the filter,
            see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
            (default None)

        Returns
        -------
        None
        """
        self._ensure_sheet(sheet)

        self.spread.batch_update(
            {"requests": create_merge_cells_request(self.sheet.id, start, end)}
        )

        self.refresh_spread_metadata()

    def unmerge_cells(self, start="A1", end=None, sheet=None):
        """
        Unmerge all cells between the start and end cells. Use defaults to unmerge all
        cells in the sheet.

        Parameters
        ----------
        start : tuple,str
            Tuple indicating (row, col) or string like 'A1' (default A1)
        end : tuple,str
            Tuple indicating (row, col) or string like 'A1' (default last cell in sheet)
        sheet : str,int,Worksheet
            optional, if you want to open or create a
            different sheet before adding the filter,
            see :meth:`open_sheet <gspread_pandas.spread.Spread.open_sheet>`
            (default None)

        Returns
        -------
        None
        """
        self._ensure_sheet(sheet)

        if end is None:
            end = self.get_sheet_dims()

        self.spread.batch_update(
            {"requests": create_unmerge_cells_request(self.sheet.id, start, end)}
        )

        self.refresh_spread_metadata()

    def add_permission(self, permission):
        """
        Add a permission to the current spreadsheet.

        The format should be:
        ``<id>|(<group>)|(<role>)|(<notify>)|(<require_link>)`` where:

        - ``<id>`` - email address of group or individual, domain, or 'anyone'
        - ``<group>`` - optional, if the id is a group e-mail, this needs to be
          'group' or 'grp'
        - ``<role>`` - optional, one of 'owner', 'writer', or 'reader'. If ommited,
          'reader' will be used
        - ``<notify>`` - optional, if you don't want to notify the user, pass 'no'
          or 'false'
        - ``<require_link>`` - optional, if you want to require the user to have
          the link, pass 'link'

        For example, to allow anyone with a link in the group admins@example.com to
        write when they have a link, but without sending a notification to the group:
        ``admins@example.com|grp|owner|false|link``

        Or if you want to give user@example.com reader permissions without a
        notification:
        ``user@example.com|no``

        Or to give anyone read access:
        ``anyone``

        Parameters
        ----------
        permissions : string
            A strings meeting the above mentioned format.


        Returns
        -------
        None
        """
        perm = parse_permission(permission)
        self.client.insert_permission(self.spread.id, perm.pop("value", None), **perm)

    def add_permissions(self, permissions):
        """
        Add permissions to the current spreadsheet. See.

        :meth:`add_permission <gspread_pandas.spread.Spread.add_permission>` for format.


        Parameters
        ----------
        permissions : list
            A list of strings meeting the above mentioned format.


        Returns
        -------
        None
        """
        for perm in permissions:
            self.add_permission(perm)

    def list_permissions(self):
        """
        List all permissions for this Spreadsheet.

        Returns
        -------
        list
            a list of dicts indicating the permissions on this spreadsheet
        """
        return self.client.list_permissions(self.spread.id)

    def move(self, path="/", create=True, folder_id=None):
        """
        Move the current spreadsheet to the specified path in your Google drive. If the
        file is not currently in you drive, it will be added.

        Parameters
        ----------
        path : str
            folder path (Default value = "/")
        create : bool
            if true, create folders as needed (Default value = True)
        folder_id : str
            optional, id of the destination folder, used instead of ``path``,
            see :meth:`move_file <gspread_pandas.client.Client.move_file>`
            (Default value = None)

        Returns
        -------
        """
        self.client.move_file(self.spread.id, path, create, folder_id)
