import json

import pytest

from gspread_pandas import conf
from gspread_pandas.util import decode

OAUTH_SECRET = {
    "installed": {
        "client_id": "id",
        "client_secret": "secret",
        "redirect_uris": ["http://localhost"],
    }
}

STORED_CREDS = {
    "refresh_token": "token",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "id",
    "client_secret": "secret",
    "scopes": [],
}


@pytest.fixture
def conf_dir(tmp_path):
    """A config directory holding a google_secret.json."""
    (tmp_path / "google_secret.json").write_text(decode(json.dumps(OAUTH_SECRET)))
    return tmp_path


@pytest.fixture
def default_dir(tmp_path, monkeypatch):
    """Point the default config location somewhere disposable."""
    default = tmp_path / "default_config"
    default.mkdir()
    monkeypatch.setenv(conf.CONFIG_DIR_ENV_VAR, str(default))
    return default


def store_creds(directory, user="default"):
    conf.ensure_path(directory)
    (directory / user).write_text(decode(json.dumps(STORED_CREDS)))


def test_get_config_reports_where_creds_will_go(conf_dir):
    """Documented since this function was written, never actually set (#104)."""
    config = conf.get_config(conf_dir=conf_dir)
    assert config["creds_dir"] == conf_dir / "creds"


def test_get_config_defaults_creds_dir_to_the_default_location(default_dir):
    (default_dir / "google_secret.json").write_text(decode(json.dumps(OAUTH_SECRET)))
    config = conf.get_config()
    assert config["creds_dir"] == default_dir / "creds"


def test_creds_are_read_from_the_configured_dir(conf_dir, default_dir):
    store_creds(conf_dir / "creds")
    config = conf.get_config(conf_dir=conf_dir)

    creds = conf.get_creds(config=config)

    assert creds.refresh_token == "token"


def test_setting_creds_dir_by_hand_is_honoured(conf_dir, default_dir, tmp_path):
    """The workaround the docs suggested, which used to silently do nothing."""
    elsewhere = tmp_path / "elsewhere"
    store_creds(elsewhere)

    config = conf.get_config(conf_dir=conf_dir)
    config["creds_dir"] = elsewhere

    assert conf.get_creds(config=config).refresh_token == "token"


def test_explicit_argument_beats_the_config(conf_dir, default_dir, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    store_creds(elsewhere)
    config = conf.get_config(conf_dir=conf_dir)

    assert conf.get_creds(config=config, creds_dir=elsewhere).refresh_token == "token"


def test_credentials_in_the_old_location_still_work(conf_dir, default_dir):
    """Nobody who already had credentials should be sent back through OAuth."""
    store_creds(default_dir / "creds")
    config = conf.get_config(conf_dir=conf_dir)

    assert conf.get_creds(config=config).refresh_token == "token"


def test_service_account_config_is_unaffected(tmp_path, default_dir, sa_config_json):
    """creds_dir is added to every config; a service account must ignore it."""
    # reuses conftest's session-scoped key rather than generating another,
    # which costs about nine seconds
    service_account = dict(
        sa_config_json,
        private_key_id="key-id",
        client_email="a@b.iam.gserviceaccount.com",
    )
    (tmp_path / "google_secret.json").write_text(decode(json.dumps(service_account)))

    config = conf.get_config(conf_dir=tmp_path)
    assert "creds_dir" in config

    creds = conf.get_creds(config=config)
    assert creds.service_account_email == "a@b.iam.gserviceaccount.com"
