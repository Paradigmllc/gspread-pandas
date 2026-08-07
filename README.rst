===============
Getting Started
===============

.. image:: https://img.shields.io/pypi/v/gspread-pandas.svg
        :target: https://pypi.python.org/pypi/gspread-pandas
        :alt: PyPI Version

.. image:: https://readthedocs.org/projects/gspread-pandas/badge/?version=latest
        :target: https://gspread-pandas.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

created by Diego Fernandez

Links:

-  `Documentation <http://gspread-pandas.readthedocs.io/>`_
-  `Source code <https://github.com/Paradigmllc/gspread-pandas>`_
-  `Short video tutorial <https://youtu.be/2yIcNYzfzPw>`_


Overview
========

A package to easily open an instance of a Google spreadsheet and
interact with worksheets through Pandas DataFrames. It enables you to
easily pull data from Google spreadsheets into DataFrames as well as
push data into spreadsheets from DataFrames. It leverages
`gspread <https://github.com/burnash/gspread/>`__ in the backend for
most of the heavylifting, but it has a lot of added functionality
to handle things specific to working with DataFrames as well as
some extra nice to have features.

The target audience are Data Analysts and Data Scientists, but it can also
be used by Data Engineers or anyone trying to automate workflows with Google
Sheets and Pandas.

Some key goals/features:

-  Be easy to use interactively, with good docstrings and auto-completion
-  Nicely handle headers and indexes (including multi-level headers and merged cells)
-  Run on Jupyter, headless server, and/or scripts
-  Allow storing different user credentials or using Service Accounts
-  Automatically handle token refreshes
-  Enable handling of frozen rows and columns
-  Enable filling in all merged cells when pulling data
-  Nicely handle large data sets and auto-retries
-  Enable creation of filters
-  Handle retries when exceeding 100 second user quota
-  When pushing DataFrames with MultiIndex columns, allow merging or flattening headers
-  Ability to handle Spreadsheet permissions
-  Ability to specify ``ValueInputOption`` and ``ValueRenderOption`` for specific columns
-  Append to a sheet, matching columns to the headers already there
-  Find where the table starts in a sheet that opens with a title or a blank row
-  Give columns their real dtypes instead of returning everything as strings


Working with messy sheets
=========================

Sheets that people actually maintain drift. A column gets renamed between
exports, someone adds a title row above the table, every value arrives as text.
Three options handle that, and all of them work with no configuration at all.

``convert_types`` gives columns their real dtypes. A column is only converted
when *every* non-empty value in it converts cleanly, so a column that is 99%
numbers and one ``N/A`` stays as text rather than quietly nulling that row::

    df = spread.sheet_to_df(convert_types=True)

``detect_layout`` finds where the table starts, for sheets that open with a
report title, a blank row, or a note to the team::

    df = spread.sheet_to_df(detect_layout=True)

``append`` adds rows below the data already in a sheet, matching your columns
to the headers that are there. Reordered or renamed columns still land in the
right place instead of being written positionally::

    spread.df_to_sheet(new_rows, append=True)

Optional: better matching with a model
--------------------------------------

Each of the three falls back to exact matching, similarity and strict type
inference, which covers most sheets on its own. Set an API key and they can
also handle renames that don't look alike (``revenue`` to ``Sales Total``),
stacked headers, and columns whose type only makes sense from the name::

    export GSPREAD_PANDAS_AI_API_KEY=...
    export GSPREAD_PANDAS_AI_BASE_URL=https://api.deepseek.com/v1  # default
    export GSPREAD_PANDAS_AI_MODEL=deepseek-chat                   # default

Any OpenAI-compatible endpoint works, so DeepSeek, OpenAI, OpenRouter, LiteLLM
and a local Ollama are all reachable by changing the base URL. No extra
packages are needed.

The model is only ever asked for a small structured answer: a column-to-header
mapping, a header row number, a type name from a fixed list. Nothing it returns
is executed, and anything naming a column, header or type that isn't really
there is discarded. A wrong answer costs you a match, never a wrong value in a
cell. Only column names and a bounded sample of rows are ever sent.

Installation / Usage
====================

To install use pip:

.. code-block:: console

    $ pip install gspread-pandas

Or clone the repo:

.. code-block:: console

    $ git clone https://github.com/aiguofer/gspread-pandas.git
    $ python setup.py install

Before using, you will need to download Google client credentials for
your app.

Client Credentials
------------------

To allow a script to use Google Drive API we need to authenticate our
self towards Google. To do so, we need to create a project, describing
the tool and generate credentials. Please use your web browser and go to
`Google console <https://console.developers.google.com/>`__ and :

-  Choose **Create Project** in popup menu on the top.
-  A dialog box appears, so give your project a name and click on
   **Create** button.
-  On the left-side menu click on **API Manager**.
-  A table of available APIs is shown. Switch **Drive API** and click on
   **Enable API** button. Do the same for **Sheets API**. Other APIs might
   be switched off, for our purpose.
-  On the left-side menu click on **Credentials**.
-  In section **OAuth consent screen** select your email address and
   give your product a name. Then click on **Save** button.
-  In section **Credentials** click on **Add credentials** and switch
   **OAuth client ID** (if you want to use your own account or enable
   the use of multiple accounts) or **Service account key** (if you prefer
   to have a service account interacting with spreadsheets).
-  If you select **OAuth client ID**:

   -  Select **Application type** item as **Desktop app** and give it a name.
   -  Click on **Create** button.
   -  Click on **Download JSON** icon on the right side of created
      **OAuth client IDs** and store the downloaded file on your file system.
-  If you select **Service account key**

   -  Click on **Service account** dropdown and select **New service account**
   -  Give it a **Service account name** and ignore the **Role** dropdown
      (unless you know you need this for something else, it's not necessary for
      working with spreadsheets)
   -  Note the **Service account ID** as you might need to give that user
      permission to interact with your spreadsheets
   -  Leave **Key type** as **JSON**
   -  Click **Create** and store the downloaded file on your file system.
-  Please be aware, the file contains your private credentials, so take
   care of the file in the same way you care of your private SSH key;
   Move the downloaded JSON to ``~/.config/gspread_pandas/google_secret.json``
   (or you can configure the directory and file name by directly calling
   ``gspread_pandas.conf.get_config``


Thanks to similar project
`df2gspread <https://github.com/maybelinot/df2gspread>`__ for this great
description of how to get the client credentials.

You can read more about it in the `configuration docs
<https://gspread-pandas.readthedocs.io/en/latest/configuration.html>`__
including how to change the default behavior.

Example
=======

.. code:: python

    import pandas as pd
    from gspread_pandas import Spread, Client

    file_name = "http://stats.idre.ucla.edu/stat/data/binary.csv"
    df = pd.read_csv(file_name)

    # 'Example Spreadsheet' needs to already exist and your user must have access to it
    spread = Spread('Example Spreadsheet')
    # This will ask to authenticate if you haven't done so before

    # Display available worksheets
    spread.sheets

    # Save DataFrame to worksheet 'New Test Sheet', create it first if it doesn't exist
    spread.df_to_sheet(df, index=False, sheet='New Test Sheet', start='A2', replace=True)
    spread.update_cells('A1', 'B1', ['Created by:', spread.email])
    print(spread)
    # <gspread_pandas.client.Spread - User: '<example_user>@gmail.com', Spread: 'Example Spreadsheet', Sheet: 'New Test Sheet'>

    # You can now first instanciate a Client separately and query folders and
    # instanciate other Spread objects by passing in the Client
    client = Client()
    # Assumming you have a dir called 'example dir' with sheets in it
    available_sheets = client.find_spreadsheet_files_in_folders('example dir')
    spreads = []
    for sheet in available_sheets.get('example dir', []):
        spreads.append(Spread(sheet['id'], client=client))

Troubleshooting
===============

EOFError in Rodeo
-----------------

If you're trying to use ``gspread_pandas`` from within
`Rodeo <https://www.yhat.com/products/rodeo>`_ you might get an
``EOFError: EOF when reading a line`` error when trying to pass in the verification
code. The workaround for this is to first verify your account in a regular shell.
Since you're just doing this to get your Oauth token, the spreadsheet doesn't need
to be valid. Just run this in shell:

.. code:: python

   python -c "from gspread_pandas import Spread; Spread('<user_key>','')"

Then follow the instructions to create and store the OAuth creds.


This action would increase the number of cells in the workbook above the limit of 10000000 cells.
-------------------------------------------------------------------------------------------------

IMO, Google sheets is not the right tool for large datasets. However, there's probably good reaons
you might have to use it in such cases. When uploading a large DataFrame, you might run into this
error.

By default, ``Spread.df_to_sheet`` will add rows and/or columns needed to accomodate the DataFrame.
Since a new sheet contains a fairly large number of columns, if you're uploading a DF with lots of
rows you might exceed the max number of cells in a worksheet even if your data does not. In order
to fix this you have 2 options:

1. The easiest is to pass ``replace=True``, which will first resize the worksheet and clear out all values.
2. Another option is to first resize to 1x1 using ``Spread.sheet.resize(1, 1)`` and then do ``df_to_sheet``

There's a strange caveat with resizing, so going to 1x1 first is recommended (``replace=True`` already does this). To read more see `this issue <https://issuetracker.google.com/issues/213126648>`_
