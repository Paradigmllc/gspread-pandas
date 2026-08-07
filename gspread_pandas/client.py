import requests
from google.auth.credentials import Credentials
from google.auth.transport.requests import AuthorizedSession
from gspread import Spreadsheet
from gspread.client import Client as ClientV4
from gspread.exceptions import APIError, SpreadsheetNotFound
from gspread.utils import finditem

from gspread_pandas.conf import default_scope, get_creds
from gspread_pandas.util import (
    add_paths,
    convert_credentials,
    folders_to_create,
    monkey_patch_request,
    remove_keys_from_list,
)

__all__ = ["Client"]


class Client(ClientV4):
    """
    The gspread_pandas :class:`Client` extends :class:`Client <gspread.client.Client>`
    and authenticates using credentials stored in ``gspread_pandas`` config.

    This class also adds a few convenience methods to explore the user's google drive
    for spreadsheets.

    Parameters
    ----------
    user : str
        optional, string indicating the key to a users credentials,
        which will be stored in a file (by default they will be stored in
        ``~/.config/gspread_pandas/creds/<user>`` but can be modified with
        ``creds_dir`` property in config). If using a Service Account, this
        will be ignored. (default "default")
    config : dict
        optional, if you want to provide an alternate configuration,
        see :meth:`get_config <gspread_pandas.conf.get_config>`
        (default None)
    scope : list
        optional, if you'd like to provide your own scope
        (default default_scope)
    creds : google.auth.credentials.Credentials
        optional, pass credentials if you have those already (default None)
    session : google.auth.transport.requests.AuthorizedSession
        optional, pass a google.auth.transport.requests.AuthorizedSession or a
        requests.Session and creds (default None)
    load_dirs : bool
        optional, whether you want to load directories and paths on instanciation.
        if you refresh directories later or perform an action that requires them,
        they will be loaded at that time. For speed, this is disabled by default
        (default False)
    """

    _email = None
    _root = None
    _dirs = None
    _load_dirs = False

    def __init__(
        self,
        user="default",
        config=None,
        scope=default_scope,
        creds=None,
        session=None,
        load_dirs=False,
    ):
        #: `(list)` - Feeds included for the OAuth2 scope
        self.scope = scope

        if isinstance(session, requests.Session):
            credentials = getattr(session, "credentials", creds)
            if not credentials:
                raise TypeError(
                    "If you provide a session, you must also provide credentials"
                )
        else:
            if isinstance(creds, Credentials):
                credentials = creds
            elif creds is not None and "oauth2client" in creds.__module__:
                credentials = convert_credentials(creds)
            elif isinstance(user, str):
                credentials = get_creds(user, config, self.scope)
            else:
                raise TypeError(
                    "Need to provide user as a string or credentials as "
                    "google.auth.credentials.Credentials"
                )
            session = AuthorizedSession(credentials)
        super().__init__(credentials, session)

        # gspread's HTTPClient only records auth when it builds the session itself,
        # so client.expiry and http_client.login() break when a session is passed in
        self.http_client.auth = credentials

        monkey_patch_request(self)

        self._root = self._drive_request(file_id="root", params={"fields": "name,id"})
        self._root["path"] = "/"

        if load_dirs:
            self.refresh_directories()

    @property
    def root(self):
        """`(dict)` - the info for the top level Drive directory for current user"""
        return self._root

    def _get_dirs(self, strip_parents=True):
        """
        Helper function to fetch directories if they haven't been yet.

        It will strip the parents by default for the `directories`
        property
        """
        if not self._load_dirs:
            self.refresh_directories()

        if strip_parents:
            # this will make a copy, if we intend to modify the values
            # internally, pass strip_parents = False
            return remove_keys_from_list(self._dirs + [self.root], ["parents"])
        else:
            return self._dirs + [self.root]

    directories = property(
        _get_dirs,
        doc=(
            "`(list)` - list of dicts for all avaliable "
            "directories for the current user"
        ),
    )

    @property
    def email(self):
        """`(str)` - E-mail for the currently authenticated user"""
        if not self._email:
            try:
                self._email = self.http_client.request(
                    "get", "https://www.googleapis.com/userinfo/v2/me"
                ).json()["email"]
            except Exception:
                print(
                    """
                    Couldn't retrieve email. Delete credentials and authenticate again
                    """
                )

        return self._email

    def refresh_directories(self):
        """Refresh list of directories for the current user."""
        self._load_dirs = True
        q = "mimeType='application/vnd.google-apps.folder'"
        self._dirs = self._query_drive(q)
        root_dirs = [self.root]

        for dir_ in self._dirs:
            # these are top level shared drives
            if "parents" not in dir_:
                dir_["path"] = dir_["name"]
            root_dirs.append(dir_)

        for root_dir in root_dirs:
            add_paths(root_dir, self._dirs)

    def login(self):
        """Override login since AuthorizedSession now takes care of automatically
        refreshing tokens when needed."""

    def _query_drive(self, q):
        files = []
        page_token = ""
        params = {
            "q": q,
            "pageSize": 1000,
            "fields": "files(name,id,parents)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }

        while page_token is not None:
            if page_token:
                params["pageToken"] = page_token

            res = self._drive_request("get", params=params)
            files.extend(res.get("files", []))
            page_token = res.get("nextPageToken", None)

        return files

    def _drive_request(
        self, method="get", file_id=None, params=None, data=None, headers=None
    ):
        url = "https://www.googleapis.com/drive/v3/files"
        if file_id:
            url += "/{}".format(file_id)
        try:
            res = self.http_client.request(method, url, params=params, json=data)
            if res.text:
                return res.json()
        except APIError as e:
            if "scopes" in e.response.text:
                print(
                    "Your credentials don't have Drive API access, ignoring "
                    "drive specific functionality (Note this includes searching "
                    "spreadsheets by name)"
                )
                return {}
            raise

    def open(self, title):
        """
        Opens a spreadsheet.

        :param title: A title of a spreadsheet.
        :type title: str

        :returns: a :class:`~gspread.spreadsheet.Spreadsheet` instance.

        If there's more than one spreadsheet with same title the first one
        will be opened.

        :raises gspread.SpreadsheetNotFound: if no spreadsheet with
                                             specified `title` is found.

        >>> c = gspread.authorize(credentials)
        >>> c.open('My fancy spreadsheet')
        """
        try:
            properties = finditem(
                lambda x: x["name"] == title, self.list_spreadsheet_files(title)
            )

            # Drive uses different terminology
            properties["title"] = properties["name"]

            return Spreadsheet(self.http_client, properties)
        except StopIteration:
            raise SpreadsheetNotFound

    def list_spreadsheet_files(self, title=None):
        """
        Return all spreadsheets that the user has access to.

        Parameters
        ----------
        title : str
            name of the spreadsheet, if none is passed it'll return every file
            (default None)

        Returns
        -------
        list
            List of spreadsheets. Each spreadsheet is a dict with the following keys:
            id, kind, mimeType, and name.
        """
        q = "mimeType='application/vnd.google-apps.spreadsheet'"
        if title:
            q += ' and name = "{}"'.format(title)
        return self._list_spreadsheet_files(q)

    def list_spreadsheet_files_in_folder(self, folder_id):
        """
        Return all spreadsheets that the user has access to in a sepcific folder.

        Parameters
        ----------
        folder_id : str
            ID of a folder, see :meth:`find_folders <find_folders>`

        Returns
        -------
        list
            List of spreadsheets. Each spreadsheet is a dict with the following keys:
            id, kind, mimeType, and name.
        """
        q = (
            "mimeType='application/vnd.google-apps.spreadsheet'"
            " and '{}' in parents".format(folder_id)
        )

        return self._list_spreadsheet_files(q)

    def _list_spreadsheet_files(self, q):
        """Helper function to actually run a query, add paths if needed, and remove
        unwanted keys from results."""
        files = self._query_drive(q)

        if self._load_dirs:
            self._add_path_to_files(files)

        return remove_keys_from_list(files, ["parents"])

    def _add_path_to_files(self, files):
        """Add path to files by looking up the parent dir and its path."""
        for fil3 in files:
            try:
                # if a file is in multiple directories then it'll
                # have multiple parents. However, this adds complexity
                # so we'll just choose the first one to build the path
                parent = next(
                    directory
                    for directory in self._get_dirs(False)
                    if directory["id"] in fil3.get("parents", None)
                )

                if parent is None:
                    # This is a top level shared drive
                    fil3["path"] = f"{fil3['name']}/"
                else:
                    fil3["path"] = parent.get("path", "/")
            except StopIteration:
                # Files that are visible to a ServiceAccount but not
                # in the root will not have the 'parents' property
                fil3["path"] = None

    def find_folders(self, folder_name_query=""):
        """
        Return all folders that the user has access to containing ``folder_name_query``
        in the name.

        Parameters
        ----------
        folder_name_query : str
            Case insensitive string to search in folder name. If empty,
            it will return all folders.

        Returns
        -------
        list
            List of folders. Each folder is a dict with the following keys:
            id, kind, mimeType, and name.
        """
        return [
            folder
            for folder in self.directories
            if folder_name_query.lower() in folder["name"].lower()
        ]

    def find_spreadsheet_files_in_folders(self, folder_name_query):
        """
        Return all spreadsheets that the user has access to in all the folders that
        contain ``folder_name_query`` in the name. Returns as a dict with each key being
        the folder name and the value being a list of spreadsheet files.

        Parameters
        ----------
        folder_name_query : str
            Case insensitive string to search in folder name

        Returns
        -------
        dict
            Spreadsheets in each folder. Each entry is a dict with the folder name as
            the key and a list of spreadsheets as the value. Each spreadsheet is a dict
            with the following keys: id, kind, mimeType, and name.
        """

        return {
            res["name"]: self.list_spreadsheet_files_in_folder(res["id"])
            for res in self.find_folders(folder_name_query)
        }

    def create_folder(self, path, parents=True):
        """
        Create a new folder in your Google drive.

        Parameters
        ----------
        path : str
            folder path
        parents : bool
            if True, create parent folders as needed (Default value = True)

        Returns
        -------
        dict
            information for the created directory
        """
        parent, to_create = folders_to_create(path, self._get_dirs(False))

        if len(to_create) > 1 and parents is not True:
            raise Exception(
                "If you want to create nested directories pass parents=True"
            )

        for directory in to_create:
            parent = self._drive_request(
                "post",
                params={"fields": "name,id,parents"},
                data={
                    "mimeType": "application/vnd.google-apps.folder",
                    "name": directory,
                    "parents": [parent["id"]],
                },
                headers={"Content-Type": "application/json"},
            )

        self.refresh_directories()
        return parent

    def move_file(self, file_id, path="/", create=False, folder_id=None):
        """
        Move a file to the given path.

        Parameters
        ----------
        file_id : str
            file id
        path : str
            folder path. A path starting with `/` will use your drive, for shared drives
            the path will start with `<Shared Drive Name>/` (no leading /)
        create : bool
            whether to create any missing folders (Default value = False)
        folder_id : str
            optional, id of the destination folder, used instead of ``path``.
            Names aren't unique in Drive and a folder shared with you may not
            show up in a path lookup at all, so an id is the only way to name
            some destinations (Default value = None)

        Returns
        -------
        """
        if folder_id is None:
            if path == "/":
                folder_id = "root"
            else:
                parent, missing = folders_to_create(path, self._get_dirs(False))
                if missing:
                    if not create:
                        raise Exception("Folder does not exist")

                    parent = self.create_folder(path)
                folder_id = parent["id"]

        old_parents = self._drive_request(
            "get", file_id, params={"fields": "parents"}
        ).get("parents", [])

        params = {"addParents": folder_id, "removeParents": ",".join(old_parents)}
        self._drive_request("patch", file_id, params)
