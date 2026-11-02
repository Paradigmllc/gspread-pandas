import os
from pathlib import PosixPath, WindowsPath

import pytest
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

from gspread_pandas import conf, exceptions


def test_get_config_dir():
    conf_dir = conf.get_config_dir()
    if os.name == "nt":
        assert isinstance(conf_dir, WindowsPath)
        assert "AppData" in str(conf_dir)
    else:
        assert isinstance(conf_dir, PosixPath)
        assert ".config" in str(conf_dir)


class Test_get_config:
    def test_no_file(self):
        with pytest.raises(IOError):
            conf.get_config(file_name="this_file_doesnt_exist")

    def test_with_oauth(self, oauth_config):
        c = conf.get_config(*oauth_config)
        assert isinstance(c, dict)
        assert set(c) == {"installed", "creds_dir"}
        assert len(c["installed"]) > 1

    def test_with_sa(self, sa_config):
        c = conf.get_config(*sa_config)
        assert isinstance(c, dict)
        assert len(c) > 1


class Test_get_creds:
    def test_service_account(self, set_sa_config):
        creds = conf.get_creds()
        assert isinstance(creds, ServiceAccountCredentials)

    def test_oauth_no_key(self, set_oauth_config):
        with pytest.raises(exceptions.ConfigException):
            conf.get_creds(user=None)

    def test_oauth_first_time(self, mocker, set_oauth_config, creds_json):
        mocked = mocker.patch.object(conf.InstalledAppFlow, "run_local_server")
        mocked.return_value = OAuth2Credentials.from_authorized_user_info(creds_json)
        conf.get_creds()
        # python 3.5 doesn't have assert_called_once
        assert mocked.call_count == 1
        assert mocked.call_args.kwargs["port"] == 8182
        assert (conf.get_config_dir() / "creds" / "default").exists()
    
    def test_oauth_first_time_override_port(self, mocker, set_oauth_config, creds_json, monkeypatch):
        """We must be able to override the local port used to authenticate"""
        new_port = 9000
        monkeypatch.setenv(conf.OAUTH_SERVER_PORT_ENV_VAR, str(new_port))
        mocked = mocker.patch.object(conf.InstalledAppFlow, "run_local_server")
        mocked.return_value = OAuth2Credentials.from_authorized_user_info(creds_json)
        conf.get_creds()
        # python 3.5 doesn't have assert_called_once
        assert mocked.call_count == 1
        assert mocked.call_args.kwargs["port"] == new_port

    def test_oauth_first_time_no_save(self, mocker, set_oauth_config):
        mocker.patch.object(conf.InstalledAppFlow, "run_local_server")
        conf.get_creds(save=False)
        # python 3.5 doesn't have assert_called_once
        assert conf.InstalledAppFlow.run_local_server.call_count == 1

    def test_oauth_default(self, make_creds):
        assert isinstance(conf.get_creds(), OAuth2Credentials)

    @pytest.mark.skip(reason="need to fix this test")
    def test_bad_config(self, set_sa_config):
        with pytest.raises(exceptions.ConfigException):
            conf.get_creds(config={"foo": "bar"})
