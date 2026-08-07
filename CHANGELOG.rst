Change Log
==========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <http://keepachangelog.com/>`_
and this project adheres to `Semantic Versioning <http://semver.org/>`_.

[Unreleased]
------------

Fixed
-----

- ``Spread.clear_sheet`` left the frozen rows and columns populated. Clearing
  works by shrinking the sheet and growing it back, but a sheet can't shrink
  past its frozen block, so that block survived and only ``A1`` was cleared
  (#97)
- ``get_config`` now sets ``creds_dir``, and ``get_creds`` now reads it. Both
  were documented from the start and neither was implemented, so pointing
  ``conf_dir`` somewhere custom — or setting ``creds_dir`` by hand, as the
  docstring suggested — silently left credentials in the default location
  (#104). Credentials already in the old location are still read, so nobody
  is sent back through the OAuth flow

[4.0.0] - 2026-08-07
-----------------------------

Breaking
--------

- Requires gspread 6. ``Client.auth`` is now ``Client.http_client.auth``,
  following gspread's move of HTTP execution into a separate ``HTTPClient``
- Requires Python 3.9. gspread 6 needs 3.8 and pandas 2 needs 3.9, so the
  older versions the package still advertised could not have worked

Added
-----

- ``append`` option for ``Spread.df_to_sheet``, adding rows below the data
  already in a sheet and matching columns to the headers there rather than
  writing them positionally (#86)
- ``convert_types`` option for ``Spread.sheet_to_df``, giving columns their
  real dtypes instead of returning everything as ``object`` (#18)
- ``detect_layout`` option for ``Spread.sheet_to_df``, finding where the table
  starts in a sheet that opens with a title or a blank row
- Optional use of an OpenAI-compatible model for the harder cases of all
  three, enabled with ``GSPREAD_PANDAS_AI_API_KEY``. Adds no dependencies,
  and every feature works without it
- ``-1`` for ``unformatted_columns`` and ``formula_columns`` on
  ``Spread.sheet_to_df``, meaning every column (thanks @ChristophBoerlin, #56)
- ``folder_id`` for ``Client.move_file`` and ``Spread.move``, for destinations
  a path can't name (thanks @dtquandt, #48)

Changed
-------

- Support gspread 6, and require it. gspread 6 moved HTTP execution out of
  ``Client`` into ``HTTPClient``, so ``Client.auth`` is now
  ``Client.http_client.auth``

Fixed
-----

- Rate limit auto-retry no longer silently stops retrying. It matched against
  ``str(APIError)``, which no longer carries the status field in gspread 6
- ``Client.expiry`` and ``http_client.login()`` no longer fail with
  ``AttributeError``; gspread only records ``auth`` when it builds the session
  itself, and gspread-pandas always passes one in
- ``Spread.sheet_to_df`` no longer raises a pandas ``FutureWarning`` about
  silent downcasting when a sheet has a column of blanks (thanks
  @IvanKaramazov, #102, #103)

[3.3.0] - 2024-02-13
-----------------------------

Changed
-------

- Limit gspread version to < 6.0

[3.2.3] - 2023-08-30
-----------------------------

Added
-----

- Add ``merge_index`` option for ``Spread.df_to_sheet``

[3.2.2] - 2022-06-29
-----------------------------

Changed
-------

- Update CI and its documentation


[3.2.1] - 2022-06-29
-----------------------------

Fixed
-----

- Don't use the deprecated pandas option ``inplace = True``
- Fix hanging auth test
- Example in docs

Removed
-------

- Fix for early pandas 1.0 is no longer necessary

[3.2.0] - 2022-03-19
-----------------------------
[3.1.0] - 2022-03-19
-----------------------------

Fixed
-----

- OOB auth flow was removed from google-auth, `see here <https://developers.googleblog.com/2022/02/making-oauth-flows-safer.html#disallowed-oob>`_. Fixed it by running local server to listen for token.

[3.0.4] - 2022-01-18
-----------------------------

Fixed
-----

- Frozen column field in ``gridProperties`` changed from ``frozenColCount`` to ``frozenColumnCount``

[3.0.3] - 2022-01-04
-----------------------------

Fixed
-----

- Potential issue with resizing in ``clear_sheet``

Added
-----

- Section about resizing issues to README

[3.0.2] - 2021-12-29
-----------------------------

Removed
-------

- Remove deprecated param raw_column_names

[3.0.1] - 2021-12-28
-----------------------------

Changed
-------

- Pipeline changes

[3.0.0] - 2021-12-28
-----------------------------

Changed
-------

- Upgrade gspread to >= 5

Removed
-------

- BREAKING: Removed Python 2.7 support
- Removed Travis pipeline

Added
-----

- CI pipeline using Github Actions

[2.3.1] - 2021-11-29
-----------------------------

Fixed
-----

- Fix gspread 5 incompatibility by blocking requirements

[2.3.0] - 2021-03-21
-----------------------------

Changed
-------

- Switch to pycryptodome instead of pycrypto to fix tests
- Switch from future to six for python 2 compat

Fixed
-----

- Fix docstring about default sheet param for `open`
- Fix numpy deprecation warning about numeric-style types
- Fix google quota exceed retry

Added
-----

- Added ability to use shared drives

[2.2.4] - 2021-01-24
-----------------------------

Fixed
-----

- Fix dtype issues for numeric+null values for pandas 1.0
- Fix auth within Colab

[2.2.3] - 2020-03-26
-----------------------------

Fixed
-----

- Ensure we respect XDG_CONFIG_HOME
- Use current dir if no $HOME env var is set (in some cloud environments and Colab)

[2.2.2] - 2020-03-21
-----------------------------

Changed
-------

- Use Path for various paths in conf.py

[2.2.1] - 2020-01-05
-----------------------------

Added
-----

-  Added a section explaining the main concepts of ``Gspread-Pandas``
   to the docs.

Fixed
-----

-  Fixed the auto-retry when encountering the 100 second quota limit (thanks @rodelrod).
-  All ``Client`` objects should now be monkeypatched to retry on 100 s quota error.
   Before it was only those within a ``Spread`` instance.

Changed
-------

-  When a ``Spread`` is opened, it will now open the first worksheet by default.

[2.2.0] - 2019-11-17
-----------------------------

Added
-----

-  Added ``formula_columns`` and ``unformatted_columns`` as options to
   ``Spread.sheet_to_df`` to allow usage of ValueRenderOption for specific
   columns.
-  Added test for python 3.7 and 3.8 in travis

Fixed
-----

-  Bug with certain functions when index=False
-  Bug when all columns are ``raw_columns``
-  Fixed travis tests

Deprecated
----------

-  ``raw_column_names`` is deprecated in favor of ``raw_columns``. It will
   be removed in v3.

Changed
-------

-  bumpversion config now in setup.cfg
-  Docstrings now use docformatter format


[2.1.3] - 2019-08-25
-----------------------------

Added
-----

-  Added ``Spread.add_permission`` to differentiate adding a single
   permission vs adding multiple permissions.

Changed
-------

-  Ensure license is packaged with sdist
-  Unified and simplified project and test configuration settings

[2.1.2] - 2019-07-10
-----------------------------

Added
-----

-  Added test for open_sheet

Fixed
-----

-  Client directories property now works as expected
-  Various fixes for tests

Changed
-------

-  Tox must run correctly before being able to push a new tag

[2.1.1] - 2019-07-10
-----------------------------

Fixed
-----

-  Fixed import in Spread after refactor, oops! should have ran tests

[2.1.0] - 2019-07-10
-----------------------------

Added
-----

-  Client now has an optional ``load_dirs`` param which default to ``False``

Changed
-------

-  BREAKING: Refactored ``Spread`` into its own file. If you were importing
   like ``from gspread_pandas.client import Spread`` you will need to change
   to ``from gspread_pandas.spread import Spread``.
-  Directories and paths are no longer loaded by default. However, if you try
   to use any functionality that requires it, it'll load it at that point.

Fixed
-----

-  If a file doesn't have ``parents`` it'll no longer break (thanks @shredding)
   (`#29 <https://github.com/aiguofer/gspread-pandas/issues/29>`_)
-  $XDG_CONFIG_HOME should now be respected
-  If you don't have Drive API access in the scope, it should now still work and
   print a message instead


[2.0.0] - 2019-06-12
-----------------------------

Added
-----

-  Test python 3.7, Windows, and MacOS
-  You can now iterate over worksheets like: ``for sheet in spread``
-  ``Spread.df_to_sheet`` can now flatten multi-level headers using the
   ``flatten_headers_sep`` param
-  Add ability to set permissions on spreadsheets
-  Add ability to create and move folders and spreadsheets
-  A session can now be passed directly to a ``Client``
-  A ``raw_column_names`` param to ``Spread.df_to_sheet`` to force specific
   columns to be sent to the Google Sheets API as RAW input so it doesn't
   get interpreted as a number, date, etc.

Removed
-------

-  BREAKING: Removed ``start/end_row/col`` params from add_filter
-  BREAKING: Removed ``user_creds_or_client`` param from Spread
-  BREAKING: Removed ``user_or_creds`` param from Client

Changed
-------

-  The ``credentials`` param is now called ``creds`` everywhere
-  Test suite is now a lot more robust
-  Use google-auth instead of the now deprecated oauth2client library.
   This moves the retry code into that library.
-  Default config will now be in ``C:\Users\<user>\AppData\gspread_pandas``
   on Windows


Fixed
-----

-  Things should now work when passing a ``Worksheet`` object to ``Spread.open``


[1.3.1] - 2019-05-17
-----------------------------

Fixed
~~~~~

-  Passing 0 to ``sheet``` param in any function should work now
-  When using multi-row column headers in a spreadsheet, the index name
   should now be better identified
-  Spread;update_cells should now work when passing a single cell value
-  When start != 'A1', freeze_rows/headers should now correctly freeze
   the right amount of rows/headers so the index and columns are frozen

[1.3.0] - 2019-04-30
-----------------------------

Added
~~~~~

-  Function to merge_cells
-  Function to unmerge_cells
-  Option to merge_headers in df_to_sheet
-  Retry when exceeding the 100s quota

Fixed
~~~~~

-  Fix passing 0 for freeze_index or freeze_headers. This essentially
   "unfreezes"
-  When the index has no name and you have a multi-level header, it will
   no longer fill in "index" as the index header

Deprecated
~~~~~~~~~~

-  Spread will no longer use the 'user_creds_or_client' param in v2. Instead, it
   will have optional 'credentials', 'client', and 'user' params. If creds or a
   client are passed, the user will be ignored. Otherwise, it'll use the user,
   which will default to "default"
-  Client will no longer use the 'user_or_creds' param in v2. Instead, it
   will have optional 'credentials' and 'user' params. If creds passed, the user
   will be ignored. Otherwise, it'll use the user, which will default to "default"
-  Spread.add_filter will be standardized to use 'start' and 'end' like other
   functions and the start/end_row/col are deprecated and will be removed in v2

Changed
~~~~~~~

-  Exceptions are no longer raised while handling another exception. This should
   prevent the "During handling of the above exception, another exception occurred"
   message
-  When opening a new Spreadsheet, the SpreadsheetNotFound exception will no longer
   be a "catchall" for any errors. If an error other than actually not finding the
   Spreadsheet occurs, it'll be raised.
-  Default value for the user param in util.get_config was changed to "default"

[1.2.2] - 2019-04-15
-----------------------------

Fixed
~~~~~

-  Fix passing only one of freeze_index or freeze_headers = True

[1.2.1] - 2018-08-30
-----------------------------

Fixed
~~~~~

-  Fixed __version__ string for bumpversion using black

[1.2.0] - 2018-08-30
-----------------------------

Added
~~~~~

-  Add config files and pre-commit hooks for isort, black, and flake8
-  Add config files for isort, black, and flake8

Fixed
~~~~~

-  Fixed clear_sheet when there are frozen rows/cols
-  Small fixes in README

Changed
~~~~~~~

-  Changed from reST docstrings to numpy docstrings
-  Updated README to include more in contributing section

[1.1.3] - 2018-07-07
-----------------------------

Added
~~~~~

-  Added unit tests for util

Fixed
~~~~~

-  Fix parse_df_col_names when df has a multi-index
-  Fix parse_sheet_index when using last column as index
-  Fix fillna when using categorical variables

[1.1.2] - 2018-06-23
-----------------------------

Fixed
~~~~~

-  Fix issue with basestring usage

Changed
~~~~~~~

-  Remove Python 3.4 from travis tests

[1.1.1] - 2018-06-13
-----------------------------

Changed
~~~~~~~

-  ``Spread.clear_sheet`` now doesn't resize to 0 since V4 is much more efficient at making batch updates. This should help prevent formulas that point to these sheets from breaking.

[1.1.0] - 2018-06-02
-----------------------------

Fixed
~~~~~

-  Now works with gspread 3.0
-  Spread.freeze is working again

Changed
~~~~~~~

-  Moved a lot of the credential handling into functions in gspread_pandas.conf
-  New ``get_creds`` function allows you to get ``OAuth2Credentials`` and pass them in to a ``Client`` or ``Spread``
-  Some functions were moved to ``gspread_pandas.util``

Added
~~~~~

-  New function ``Spread.add_filter`` created so that you can add filters to worksheets
-  New param ``add_filter`` added to ``Spread.df_to_sheet`` to add a filter to uploaded data

[1.0.5] - 2018-04-14
-----------------------------

Fixed
~~~~~

-  Added limit to gspread version since 3.0 broke gspread-pandas

[1.0.4] - 2018-04-08
-----------------------------

Fixed
~~~~~

-  Change ValueInputOption to USER_ENTERED so dates and numbers are parsed correctly in Google Sheets

[1.0.3] - 2018-04-02
-----------------------------

Added
~~~~~

-  Basic initial test

[1.0.2] - 2018-04-02
-----------------------------

Changed
~~~~~~~

-  Some dependency changes
-  Travis deploy will only happen on python 3.6
-  Changes to reduce number of fetch_sheet_metadata calls

[1.0.1] - 2018-03-26
-----------------------------

Changed
~~~~~~~

-  Replace pypi-publisher with twine in dev reqs
-  Change download url, now it should match the tags from bumpversion

[1.0.0] - 2018-03-26
-----------------------------

Added
~~~~~

-  There is now a separate ``Client`` class that extends the gspread v4 Client class and adds some functionalty. This includes a monkeypatche and hacky workarounds for gspread 2.0 issues. Once they get fixed upstream I need to remove these.

Changed
~~~~~~~

-  Now supports gspread 2.0 which uses Spreadsheets V4 API, this provides much better performance and reliability. Some APIs might have changed.
-  No longer need to chunk update requests, and range requests can use larger chunks
-  Some code improvements enabled by gspread 2.0
-  Removed deprecated params and functions

[0.16.1] - 2018-03-24
-----------------------------

Fixed
~~~~~

-  Set up correct credentials for travis pypi push

[0.16.0] - 2018-03-24
-----------------------------

Added
~~~~~

-  Test on multiple versions using tox
-  Enable travis-ci

Fixed
~~~~~

-  Remove dir accidentally pushed by build

Changed
~~~~~~~

-  Moved dev requirements into requirements_dev.txt
-  Now using bumpversion for version management
-  Minor updates to README
-  Documentation now at Read The Docs
-  Minor code changes to please flake8
-  Deleted update_pypi.sh as releases are now handled by travis

[0.15.6] - 2018-03-12
-----------------------------

Fixed
~~~~~

-  Remove code accidentally pushed by build

[0.15.5] - 2018-03-12
-----------------------------

Fixed
~~~~~

-  Added dependency version limit for gspread; will remove in next version

[0.15.4] - 2018-02-13
-----------------------------

Fixed
~~~~~

-  README example now points to the correct URL (thanks @lionel)
-  Calling parse_sheet_headers on an empty sheet doesn't break anymore (thanks @taewookim)

Added
~~~~~

-  You can now use service account credentials in the config (thanks @marcojetson)

[0.15.3] - 2017-11-21
-----------------------------

Changed
~~~~~~~

-  Always return an Index object from parse_sheet_headers

[0.15.2] - 2017-11-18
-----------------------------

Fixed
~~~~~

-  Fix sheet_to_df when headers are present with no data

Changed
~~~~~~~

-  Minimum Pandas version .20 now required

[0.15.1] - 2017-10-05
-----------------------------

Fixed
~~~~~

-  When there are merged cells outside the data range, an exception is no longer
   thrown.
-  Cast keys() to a list to fix Python 3 compat

[0.15.0] - 2017-09-11
-----------------------------

Changed
~~~~~~~

-  Added ``fill_value`` option to df_to_sheet

Fixed
~~~~~

-  Different application type credentials can be used now
-  Some safeguards to prevent certain exceptions
-  df_to_sheet won't fail when categorical columns have nulls

[0.14.3] - 2017-06-22
-----------------------------

Changed
~~~~~~~

-  Force gspread sheets refresh when refreshing sheets
-  Worksheet object can now be passed it to most functions with ``sheet`` param

[0.14.2] - 2017-06-18
-----------------------------

Added
~~~~~

-  Added ``url`` property for easy linking

Fixed
~~~~~

-  Fixed retry for _retry_get_all_values

[0.14.1] - 2017-06-05
-----------------------------

Changed
-------

-  Ensure sheet matadata is refreshed after sheet changing activitiesthrough use of a
   decorator
-  Retry when calling ``get_all_values``
-  More robust way to get index when a new sheet is created

[0.14.0] - 2017-05-25
-----------------------------

Added
~~~~~

-  Added function to freeze rows/columns to ``Spread``
-  Added ``freeze_index`` and ``freeze_headers`` flags to ``df_to_sheet``

Changed
~~~~~~~

-  Don't re-size again when using ``replace=True``
-  Switch away from deprecated ``gspread`` functions
-  Make functions in ``util`` non-private

Fixed
~~~~~

-  Prevent error when index > number of columns in ``sheet_to_df``

[0.13.0] - 2017-04-28
-----------------------------

Added
~~~~~

-  Added ``create_spread`` and ``create_sheet`` params for ``Spread`` class. This enables
   creating a spreadsheet or a worksheet during opening. This will require re-authenticating
   in order to use it

[0.12.1] - 2017-04-25
-----------------------------

Changed
~~~~~~~

-  If using multi-level headings, heading will be shifted up so the top level
   is not a blank string
-  Some functions that don't depend on ``self`` were moved into ``util.py``
-  The ``headers`` param in ``sheet_to_df`` was deprecated in favor of ``header_rows``

Fixed
~~~~~

-  I introduced some small bugs with the v4 api changes when a sheet is not found,
   they now work as expected even when a new sheet is created
-  The list of sheets is now refreshed when one is deleted

[0.12.0] - 2017-03-31
-----------------------------

Added
~~~~~

-  Add Sheets API v4 client to ``self.clientv4``

Fixed
~~~~~

-  Merged cells now all get the right value in ``sheet_to_df``
-  You can now pass ``replace=True`` when a sheet has frozen rows/cols

[0.11.2] - 2017-03-22
-----------------------------

Changed
~~~~~~~

-  Minor change to README

[0.11.1] - 2017-03-22
-----------------------------

Added
~~~~~

-  Added note about ``EOFError`` when verifying Oauth in ``Rodeo``

Changed
~~~~~~~

-  Add retry method for ``sheet.range`` to work around 'Connection Broken' error

Fixed
~~~~~

-  Fixed clearing only rows with ``clear_sheet``

[0.11.0] - 2017-02-14
-----------------------------

Changed
~~~~~~~

-  Only clear up to first row in ``clear_sheet`` so that data filters will persist
-  Moved default config from ``~/.google/`` to ``~/.config/gspread_pandas``

Fixed
~~~~~

-  Allow passing index ``0`` to ``open``
-  Fixed changelog

[0.10.1] - 2017-01-26
-----------------------------

Added
~~~~~

-  Added troubleshooting for ``certifi`` issue in ``README``

Changed
~~~~~~~

-  Only catch ``SpreadsheetNotFound`` exceptions when opening a spreadsheet


[0.10.0] - 2017-01-18
-----------------------------

Added
~~~~~

-  Added optional ``create`` param to ``open_sheet`` to create it if it doesn't exist
-  Added optional ``start`` param to ``df_to_sheet``, will take tuple or address as str

Changed
~~~~~~~

-  Improved docs, changed to ``rst``
-  Made some variables private
-  Improved ``__str__`` output
-  Switch to using exceptions from ``gspread``
-  ``spread`` param is now required for ``open``
-  When current sheet is deleted, ``self.sheet`` is set to ``None``
-  Improved versioning, switched to `Semantic Versioning <http://semver.org/>`_

Fixed
~~~~~

-  Fixed chunk calculation in Python 3
-  Sheet names are case insensitive, fixed ``find_sheet``

Deprecated
~~~~~~~~~~

-  Deprecate ``open_or_create_sheet`` function in favor of ``create=True`` param
   for ``open_sheet``
-  Deprecate ``start_row`` and ``start_col`` in ``df_to_sheet`` in favor of ``start``
   param

[0.9] - 2016-12-07
-----------------------------

Added
~~~~~

-  Add ``__repr__`` and ``__str__`` to show the active
-  Add user's email as a property to Spread. I recommend deleting
   existing Oauth credentials and re-creating them with new permissions
-  Allow importing with: ``from gspread_pandas import Spread``
-  Added ``CHANGELOG.md``

Changed
~~~~~~~

-  Restrict scope to only necessary endpoints
-  Add retry for updating cells in case an error occurrs
-  Minor changes to ``README.md``

Fixed
~~~~~

-  Fixed the use of ``start_row`` > 1

[0.8] - 2016-11-11
-----------------------------

Added
~~~~~

-  Add python 3 build to ``update_pypi.sh`` script

Fixed
~~~~~

-  Oauth flow now uses correct properties

[0.7] - 2016-11-10
-----------------------------

Changed
~~~~~~~

-  Made python 3 compatible using future

[0.6] - 2016-10-27
-----------------------------

Changed
~~~~~~~

-  Change defaults in ``sheet_to_df`` to include index and header
-  Raise error when missing google client config file

[0.5] - 2016-10-19
-----------------------------

Changed
~~~~~~~

-  Improve decorators more using ``decorator.decorator``

[0.4] - 2016-10-19
-----------------------------

Added
~~~~~

-  Pypi update script

Changed
-------

-  Improve decorators using ``functools.wraps``

[0.3] - 2016-10-19
-----------------------------

Changed
~~~~~~~

-  Add ``ensure_auth`` decorator to most functions to re-auth if needed
-  Chunk requests to prevent timeouts
-  Improved ``clear_sheet`` by resizing instead of deleting and
   re-creating

[0.2] - 2016-10-12
-----------------------------

Added
~~~~~

-  Code migrated
-  Example usage in README
-  Add requirements

[0.1] - 2016-10-11
-----------------------------

Added
~~~~~

-  README
-  initial code migrated
