Configuration
=============

By default, the configuration will be in ``$HOME/.config/gspread_pandas`` on Nix systems and
``%APPDATA%\gspread_pandas`` on Windows. Under the default behavior, you must have your Google
client credentials stored in ``google_secret.json`` in that directory. If you're not using a
Service Account, the user credentials will be stored in a subdirectory called ``creds``.

App Credentials
---------------

There's 2 main types of app credentials: OAuth client and Service Account. In order to act as
your own Google user, you will need the OAuth client app credentials. With
this type of credentials, each user will need to grant permissions to your app. When they
grant permissions, their credentials will be stored as described below.

As a Service Account, the used credentials will be for the service account itself. This means
that you'll be using the service account's e-mail and Google drive. Additionally, it will only
be able to work withSpreadsheets that it has permissions for. Although Service Accounts can be
useful for batch processes, you might generally prefer to work as your own user.


User Credentials
----------------

Once you have your client credentials, you can have multiple user
credentials stored in the same machine. This can be useful when you have
a shared server (for example with a Jupyter notebook server) with
multiple people that may want to use the library. The ``user`` parameter to
``Spread`` must be the key identifying a user's credentials, by default it
will store the creds using ``default`` as the key. The first
``get_creds`` is called for a specific key, you will have to authenticate
through a text based OAuth prompt; this makes it possible to run on a headless
server through ssh or through a Jupyter notebook. After this, the
credentials for that user will be stored in the ``creds`` subdirectory and the
tokens will berefreshed automatically any time the tool is used.

Users will only be able to interact with Spreadsheets that they have
access to.

Authentication
-----------------------

In the backend, the library is leveraging
`Google's google-auth <https://google-auth.readthedocs.io/en/latest/>`__ to
handle authentication. It conveniently stores everything as described
above so that you don't have to worry about boiler plate code to handle auth.

When a ``Client`` is instanciated, an ``AuthorizedSession`` is created using the
credentials and this is what's used to make requests to the API. This takes care
of handling token refreshes and retries for you.

Alternate Workflows
-------------------

There's a variety of ways to change the default behavior of how/where configuration is stored.

The easiest way to change the default location is to set the ``GSPREAD_PANDAS_CONFIG_DIR``
env variable to the directory where you want to store everything. If you use this, the
client creds will still need to be named ``google_secret.json`` and user creds will still
be stored in the ``creds`` subdirectory.

If you have different client credentials, you could load them passing in ``conf_dir`` and/or
``file_name`` to ``gspread_pandas.conf.get_config``. Alternatively, you could pull these from
elsewhere, like a database. Once you have the config, you could then pass that to a
``Client`` or ``Spread`` instance, or you could get credentials by passing it to
``gspread_pandas.conf.get_creds``.

When using a Service Account, the ``user`` param will be ignored in ``Client``, ``Spread`` and
``get_creds``. Otherwise, this param will be used to store the OAuth2 credentials for each user in the
creds subdirectory. If you generate your credentials elsewhere, you can pass them in to a ``Client``
or ``Spread``. You can also run through the flow to get OAuth2 and avoid saving them by calling
``get_creds`` directly. You can also override the ``creds_dir`` if you call this function.

If the default local port used for the OAuth flow is not accessible, a different port can be used
by setting the ``GSPREAD_PANDAS_OAUTH_SERVER_PORT`` env variable.
