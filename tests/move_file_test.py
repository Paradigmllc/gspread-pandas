import pytest

from gspread_pandas import Client


class FakeClient(Client):
    """A Client with only the Drive plumbing move_file touches."""

    def __init__(self, dirs=()):
        self.requests = []
        self._dirs = list(dirs)
        self._load_dirs = True
        self._root = {"id": "root", "name": "root", "path": "/"}

    def _drive_request(self, method="get", file_id=None, params=None, **kwargs):
        self.requests.append((method, file_id, params))
        if method == "get":
            return {"parents": ["old_folder"]}
        return {}


def last_patch(client):
    return next(params for method, _, params in client.requests if method == "patch")


def test_moving_to_root():
    client = FakeClient()
    client.move_file("file_id", "/")
    assert last_patch(client)["addParents"] == "root"


def test_moving_by_folder_id():
    client = FakeClient()
    client.move_file("file_id", folder_id="0ABCdef123")
    assert last_patch(client)["addParents"] == "0ABCdef123"


def test_folder_id_wins_over_path():
    """A folder id names one folder; a path may name several, or none."""
    client = FakeClient()
    client.move_file("file_id", "Some/Missing/Path", folder_id="0ABCdef123")
    assert last_patch(client)["addParents"] == "0ABCdef123"


def test_old_parents_are_removed():
    client = FakeClient()
    client.move_file("file_id", "/")
    assert last_patch(client)["removeParents"] == "old_folder"


def test_missing_path_still_raises_without_create():
    client = FakeClient()
    with pytest.raises(Exception, match="Folder does not exist"):
        client.move_file("file_id", "Nope/Missing")


def test_create_positional_argument_still_means_create():
    """move_file(id, path, True) predates folder_id and must keep working."""
    client = FakeClient()
    created = []
    client.create_folder = lambda path: created.append(path) or {"id": "new_folder"}

    client.move_file("file_id", "Brand/New", True)

    assert created == ["Brand/New"]
    assert last_patch(client)["addParents"] == "new_folder"
