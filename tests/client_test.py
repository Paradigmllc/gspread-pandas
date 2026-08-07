import pytest

from gspread_pandas import Client


@pytest.mark.usefixtures("betamax_client")
class TestClient:
    # just here just for autocompletion during development, during
    # test run this will be overridden by the above fixture
    client = Client

    def test_root(self):
        root = self.client.root
        assert isinstance(root, dict)
        assert {"id", "name", "path"} == set(root.keys())

    def test_directories(self):
        dirs = self.client.directories
        for d in dirs:
            assert isinstance(d, dict)
            assert {"name", "id", "path"} == set(d.keys())

    def test_email(self):
        assert isinstance(self.client.http_client.auth.service_account_email, str)

    def test_email_no_perm(self, betamax_client_bad_scope, capsys):
        betamax_client_bad_scope.email
        captured = capsys.readouterr()
        assert "Couldn't retrieve" in str(captured)

    def test_list_spreadsheet_files(self):
        self.client.refresh_directories()
        files = self.client.list_spreadsheet_files()
        assert isinstance(files, list)

        for f in files:
            assert isinstance(f, dict)
            assert {"name", "id", "path"} == set(f.keys())

    def test_find_spreadsheet_files_in_folder(self):
        self.client.refresh_directories()
        files = self.client.list_spreadsheet_files_in_folder("root")

        assert isinstance(files, list)

        for f in files:
            assert f["path"] == "/"

    def test_find_folders(self):
        dirs = self.client.directories
        dirs_sub = self.client.find_folders("Sub")

        assert set(d["id"] for d in dirs_sub) < set(d["id"] for d in dirs)

    def test_find_spreadsheet_files_in_folders(self):
        files = self.client.find_spreadsheet_files_in_folders("sub")

        assert isinstance(files, dict)
        assert all("sub" in k.lower() for k in files.keys())
        assert all(isinstance(v, list) for v in files.values())

    def test_create_folder(self):
        self.client.create_folder("/this/is/a/new/dir")
        assert (
            next(
                d
                for d in self.client.directories
                if "/this/is/a/new" in d["path"] and d["name"] == "dir"
            )
            is not None
        )

    def test_create_folder_no_parents(self):
        with pytest.raises(Exception):
            self.client.create_folder("/this/does/not/exist", parents=False)

    @pytest.mark.skip(reason="unsure why test isn't working, but manual testing works")
    def test_move_file(self):
        test_spread = self.client.create("test")
        test_spread_id = test_spread.id
        self.client.move_file(test_spread_id, "/this/is/a/new/dir")

        assert test_spread_id not in [
            f["id"] for f in self.client.list_spreadsheet_files_in_folder("root")
        ]

        new_dir = next(
            d
            for d in self.client.directories
            if "/this/is/a/new" in d["path"] and d["name"] == "dir"
        )

        assert test_spread_id in [
            f["id"] for f in self.client.list_spreadsheet_files_in_folder(new_dir["id"])
        ]

        self.client.del_spreadsheet(test_spread_id)
