Using Gspread-Pandas
====================

There are two main objects you will interact with in ``gspread-pandas``: the ``Client`` and the ``Spread`` objects. The goal of these objects is to make it easy to work with a variety of concepts in Google Sheets and Pandas DataFrames. A lot of care has gone into documenting functions in code to make code introspection tools useful (displaying documentation, code completion, etc).

The target audience are Data Analysts and Data Scientists, but this can also be used by Data Engineers or anyone trying to automate workflows with Google Sheets and Pandas.

Client
------

The ``Client`` extends the ``Client`` object from ``gspread`` to add some functionality. I try to contribute back to the upstream project, but some things don't make it in, and others don't belong.

The main things that are added by the ``Client`` are:

- Handling credentials and authentication to reduce boilerplate code.
- Store file paths within drive for more working with files in a more intuitive manner (requires passing ``load_dirs=True`` or calling ``Client.refresh_directories()`` if you've already instantiated a ``Client``)
- A variety of functions to query for and work with Spreadsheets in your Google Drive, mainly:

  - ``list_spreadsheet_files``
  - ``list_spreadsheet_files_in_folder``
  - ``find_folders``
  - ``find_spreadssheet_files_in_folders``
  - ``create_folder``
  - ``move_file``
- Monkey patch the request to automatically retry when there is a 100 second quota exhausted error.

You can read more :class:`in the docs for the Client object <gspread_pandas.client.Client>`.

Spread
------

The ``Spread`` object represents an open Google Spreadsheet. A ``Spread`` object has multiple Worksheets, and only one can be open at any one time. Any function you call will act on the currently open Worksheet, unless you pass ``sheet=<worksheet_name_or_index>`` when you call the function, in which case it will first open that Worksheet and then perform the action. A ``Spread`` object internally aso holds an instance of a ``Client`` to do the majority of the work.

The ``Spread`` object does a lot of stuff to make it easier for working with Google Spreadsheets. For example, it can handle merged cells, frozen rows/columns, data filters, multi-level column headers, permissions, and more. Some things can be called individually, others can be passed in as function parameters. It can also work with tuples (for example ``(1, 1)``) or A1 notation for specifying cells.

Some of the most important properties of a ``Spread`` object are:

- ``spread``: The currently open Spreadsheet (this is a ``gspread`` object)
- ``sheet``: The currently open Worksheet (this is a ``gspread`` object)
- ``client``: The ``Client`` object. This will be automatically created if one is not passed in, but you can also share the same ``Client`` instance among multiple ``Spread`` objects if you pass it in.
- ``sheets``: The list of all available Worksheets
- ``_sheet_metadata``: We store metadata about the sheet, which includes stuff like merged cells, frozen columns, and frozen rows. This is a private property, but you can refresh this with ``refresh_spread_metadata()``

Some of the most useful functions are:

- ``sheet_to_df``: Create a Pandas DataFrame from a Worksheet
- ``clear_sheet``: Clear out all values and resize a Worksheet
- ``delete_sheet``: Delete a Worksheet
- ``df_to_sheet``: Create a Worksheet from a Pandas DataFrame
- ``freeze``: Freeze a given number of rows and/or columns
- ``add_filter``: Add a filter to the Worksheet for the given range of data
- ``merge_cells``: Merge cells in a Worksheet
- ``unmerge_cells``: Unmerge cells within a range
- ``add_permission``: Add a permission to a Spreadsheet
- ``add_permissions``: Add multiple permissions to a Spreadsheet
- ``list_permissions``: Show all current permissions on the Spreadsheet
- ``move``: Move the Spreadsheet to a different location

You can read more :class:`in the docs for the Spread object <gspread_pandas.spread.Spread>`.

Sheets that don't match the shape you assumed
---------------------------------------------

Sheets that people actually maintain drift. A column gets renamed between
exports, someone adds a title row above the table, every value arrives as text.
Three options on the functions above handle that, and all of them work with no
configuration at all.

``convert_types`` gives columns their real dtypes instead of leaving everything
as ``object``. A column is only converted when *every* non-empty value in it
converts cleanly, so a column that is 99% numbers and one ``N/A`` stays as text
rather than quietly nulling that row::

    df = spread.sheet_to_df(convert_types=True)

``detect_layout`` finds where the table starts, for sheets that open with a
report title, a blank row, or a note to the team::

    df = spread.sheet_to_df(detect_layout=True)

``append`` adds rows below the data already in a sheet, matching your columns to
the headers that are there. A reordered or renamed DataFrame still lands in the
right place instead of being written positionally::

    spread.df_to_sheet(new_rows, append=True)

Optional: better matching with a model
``````````````````````````````````````

Each of the three falls back to exact matching, similarity and strict type
inference, which covers most sheets on its own. Setting an API key additionally
lets them handle renames that don't look alike (``revenue`` to ``Sales Total``),
stacked headers, and columns whose type only makes sense from the name::

    export GSPREAD_PANDAS_AI_API_KEY=...
    export GSPREAD_PANDAS_AI_BASE_URL=https://api.deepseek.com/v1  # default
    export GSPREAD_PANDAS_AI_MODEL=deepseek-chat                   # default

Any OpenAI-compatible endpoint works, so DeepSeek, OpenAI, OpenRouter, LiteLLM
and a local Ollama are all reachable by changing the base URL. No extra packages
are needed.

The model is only ever asked for a small structured answer: a column-to-header
mapping, a header row number, a type name from a fixed list. Nothing it returns
is executed, and anything naming a column, header or type that isn't really
there is discarded. A proposed type still has to survive the same strict
conversion as everything else. So a wrong answer costs you a match, never a
wrong value in a cell. Only column names and a bounded sample of rows are ever
sent, and sheet contents are treated as untrusted data rather than as
instructions.
