import json
import warnings

import numpy as np
import pandas as pd
import pytest
from google.oauth2 import credentials, service_account
from gspread.client import Client
from gspread.exceptions import APIError
from oauth2client.client import OAuth2Credentials
from oauth2client.service_account import ServiceAccountCredentials

from gspread_pandas import util

TEST = 0
ANSWER = 1
DEMO_SHEET = "1u626GkYm1RAJSmHcGyd5_VsHNr_c_IfUcE_W-fQGxIM"


@pytest.fixture
def df():
    data = [[1, 2], [3, 4]]
    cols = ["col1", "col2"]
    df = pd.DataFrame(data, columns=cols)
    df.index.name = "test_index"
    return df


@pytest.fixture
def df_empty():
    return pd.DataFrame()


@pytest.fixture
def df_multiheader():
    data = [[1, 2], [3, 4]]
    cols = pd.MultiIndex.from_tuples([("col1", "subcol1"), ("col1", "subcol2")])
    return pd.DataFrame(data, columns=cols)


@pytest.fixture
def df_multiheader_w_index():
    data = [[1, 2], [3, 4]]
    cols = pd.MultiIndex.from_tuples([("col1", "subcol1"), ("col1", "subcol2")])
    df = pd.DataFrame(data, columns=cols)
    df.index.name = "test_index"
    return df.reset_index()


@pytest.fixture
def df_multiheader_w_multiindex():
    data = [[1, 2], [3, 4]]
    cols = pd.MultiIndex.from_tuples([("col1", "subcol1"), ("col1", "subcol2")])
    ix = pd.MultiIndex.from_tuples(
        [("row1", "subrow1"), ("row1", "subrow2")], names=["l1", "l2"]
    )
    df = pd.DataFrame(data, columns=cols, index=ix)
    return df.reset_index()


@pytest.fixture
def df_multiheader_w_unnamed_multiindex():
    data = [[1, 2], [3, 4]]
    cols = pd.MultiIndex.from_tuples([("col1", "subcol1"), ("col1", "subcol2")])
    ix = pd.MultiIndex.from_tuples([("row1", "subrow1"), ("row1", "subrow2")])
    df = pd.DataFrame(data, columns=cols, index=ix)
    return df.reset_index()


@pytest.fixture
def df_multiheader_blank_top():
    data = [[1], [3]]
    cols = pd.MultiIndex.from_tuples([("", "subcol1")])
    return pd.DataFrame(data, columns=cols)


@pytest.fixture
def df_multiheader_blank_bottom():
    data = [[1], [3]]
    cols = pd.MultiIndex.from_tuples([("col1", "")])
    return pd.DataFrame(data, columns=cols)


@pytest.fixture
def data_multiheader():
    data = [
        ["", "col1", "col1"],
        ["test_index", "subcol1", "subcol2"],
        [1, 2, 3],
        [4, 5, 6],
    ]
    return data


@pytest.fixture
def data_multiheader_top():
    data = [
        ["test_index", "col1", "col1"],
        ["", "subcol1", "subcol2"],
        [1, 2, 3],
        [4, 5, 6],
    ]
    return data


@pytest.fixture
def data_empty():
    return [[]]


class Test_parse_sheet_index:
    def test_normal(self, df):
        assert util.parse_sheet_index(df, 1).index.name == "col1"

    def test_noop(self, df):
        assert util.parse_sheet_index(df, 0).index.name == "test_index"

    def test_multiheader(self, df_multiheader):
        assert util.parse_sheet_index(df_multiheader, 1).index.name == "subcol1"

    def test_multiheader2(self, df_multiheader):
        assert util.parse_sheet_index(df_multiheader, 2).index.name == "subcol2"

    def test_multiheader_blank_top(self, df_multiheader_blank_top):
        assert (
            util.parse_sheet_index(df_multiheader_blank_top, 1).index.name == "subcol1"
        )

    def test_multiheader_blank_bottom(self, df_multiheader_blank_bottom):
        assert (
            util.parse_sheet_index(df_multiheader_blank_bottom, 1).index.name == "col1"
        )


class Test_parse_df_col_names:
    def test_empty_no_index(self, df_empty):
        assert util.parse_df_col_names(df_empty, False) == [[]]

    def test_normal_no_index(self, df):
        assert util.parse_df_col_names(df, False) == [["col1", "col2"]]

    def test_multiheader_no_index(self, df_multiheader):
        expected = [["col1", "col1"], ["subcol1", "subcol2"]]
        assert util.parse_df_col_names(df_multiheader, False) == expected

    def test_multiheader_w_index(self, df_multiheader_w_index):
        expected = [["", "col1", "col1"], ["test_index", "subcol1", "subcol2"]]
        assert util.parse_df_col_names(df_multiheader_w_index, True) == expected

    def test_multiheader_w_multiindex(self, df_multiheader_w_multiindex):
        expected = [["", "", "col1", "col1"], ["l1", "l2", "subcol1", "subcol2"]]
        assert util.parse_df_col_names(df_multiheader_w_multiindex, True, 2) == expected

    def test_multiheader_no_index_flatten(self, df_multiheader):
        expected = [["col1 subcol1", "col1 subcol2"]]
        assert (
            util.parse_df_col_names(df_multiheader, False, flatten_sep=" ") == expected
        )

    def test_multiheader_w_index_flatten(self, df_multiheader_w_index):
        expected = [["test_index", "col1 subcol1", "col1 subcol2"]]
        assert (
            util.parse_df_col_names(df_multiheader_w_index, True, flatten_sep=" ")
            == expected
        )

    def test_multiheader_w_multiindex_flatten(self, df_multiheader_w_multiindex):
        expected = [["l1", "l2", "col1 subcol1", "col1 subcol2"]]
        assert (
            util.parse_df_col_names(
                df_multiheader_w_multiindex, True, 2, flatten_sep=" "
            )
            == expected
        )

    def test_multiheader_w_unnamed_multiindex_flatten(
        self, df_multiheader_w_unnamed_multiindex
    ):
        expected = [["", "", "col1 subcol1", "col1 subcol2"]]
        assert (
            util.parse_df_col_names(
                df_multiheader_w_unnamed_multiindex, True, 2, flatten_sep=" "
            )
            == expected
        )


class Test_parse_sheet_headers:
    def test_empty(self, data_empty):
        assert util.parse_sheet_headers(data_empty, 0) is None

    def test_normal(self, data_multiheader):
        expected = pd.Index(["", "col1", "col1"])
        assert util.parse_sheet_headers(data_multiheader, 1).equals(expected)

    def test_multiheader(self, data_multiheader):
        """Note that 'test_index' should be shifted up."""
        expected = pd.MultiIndex.from_arrays(
            [["test_index", "col1", "col1"], ["", "subcol1", "subcol2"]]
        )
        assert util.parse_sheet_headers(data_multiheader, 2).equals(expected)

    def test_multiheader3(self, data_multiheader):
        """Note that 'test_index' and 1 should be shifted up."""
        expected = pd.MultiIndex.from_arrays(
            [["test_index", "col1", "col1"], [1, "subcol1", "subcol2"], ["", 2, 3]]
        )
        assert util.parse_sheet_headers(data_multiheader, 3).equals(expected)


def test_chunks():
    tests = [
        (([], 1), []),
        (([1], 1), [[1]]),
        (([1, 2], 1), [[1], [2]]),
        (([1, 2, 3], 2), [[1, 2], [3]]),
    ]
    for test in tests:
        assert [chunk for chunk in util.chunks(*test[TEST])] == test[ANSWER]


def test_get_cell_as_tuple():
    tests = [("A1", (1, 1)), ((1, 1), (1, 1))]
    for test in tests:
        assert util.get_cell_as_tuple(test[TEST]) == test[ANSWER]

    bad_tests = [
        "This is a bad cell string",
        (1.0, 1.0),
        (1, 1, 1),
        {"x": "y"},
        10000000,
    ]

    for test in bad_tests:
        with pytest.raises(TypeError):
            util.get_cell_as_tuple(test)


def test_create_filter_request():
    ret = util.create_filter_request("", "A1", "A1")
    assert isinstance(ret, dict)


def test_create_frozen_request():
    ret = util.create_frozen_request("", 1, 2)
    assert isinstance(ret, dict)


def test_create_merge_cells_request():
    ret = util.create_merge_cells_request("", "A1", "A1")
    assert isinstance(ret, dict)


def test_create_unmerge_cells_request():
    ret = util.create_unmerge_cells_request("", "A1", "A1")
    assert isinstance(ret, dict)


def test_create_merge_headers_request(df_multiheader_blank_bottom):
    ret = util.create_merge_headers_request(
        "", df_multiheader_blank_bottom.columns, "A1", 0
    )
    assert isinstance(ret, list)


def test_deprecate(recwarn):
    with pytest.deprecated_call() as calls:
        util.DEPRECATION_WARNINGS_ENABLED = False
        util.deprecate("")
        assert len(calls) == 1

        util.DEPRECATION_WARNINGS_ENABLED = True
        util.deprecate("")
        assert warnings.filters[0][0] == "default"
        assert len(calls) == 2

        util.DEPRECATION_WARNINGS_ENABLED = False
        util.deprecate("")
        assert warnings.filters[0][0] == "ignore"
        assert len(calls) == 3


def test_monkey_patch_request(betamax_authorizedsession):
    c = Client(betamax_authorizedsession.credentials, betamax_authorizedsession)
    s = c.open_by_key(DEMO_SHEET)

    with pytest.raises(APIError) as excinfo:
        for i in range(200):
            s.fetch_sheet_metadata()

    assert excinfo.value.error["status"] == "RESOURCE_EXHAUSTED"
    assert "Read requests" in excinfo.value.error["message"]

    retry_delay = 10 if pytest.RECORD else 0

    util.monkey_patch_request(c, retry_delay)

    for i in range(200):
        s.fetch_sheet_metadata()


def test_get_col_merge_ranges():
    ix = pd.MultiIndex.from_arrays(
        [
            ["col1", "col1", "col2", "col2"],
            ["subcol1", "subcol1", "subcol1", "subcol1"],
            ["subsubcol1", "subsubcol2", "subsubcol2", "subsubcol2"],
        ]
    )
    assert util.get_merge_ranges(ix) == [
        [(0, 1), (2, 3)],
        [(0, 1), (2, 3)],
        [(2, 3)],
    ]


def test_fillna(df):
    df.loc[2] = [None, None]
    df.loc[3] = [np.nan, np.nan]
    df["col1"] = df["col1"].astype("category")

    assert (
        util.fillna(df, "n\a").loc[2].tolist()
        == util.fillna(df, "n\a").loc[3].tolist()
        == ["n\a", "n\a"]
    )


def test_get_range():
    assert util.get_range("a1", (3, 3)) == "A1:C3"


def test_get_contiguous_ranges():
    tests = [
        ([0], []),
        ([0, 0], [(0, 1)]),
        ([0, 1], []),
        ([0, 0, 0], [(0, 2)]),
        ([0, 0, 1], [(0, 1)]),
        ([0, 1, 1], [(1, 2)]),
        ([0, 1, 0], []),
        ([0, 0, 1, 1], [(0, 1), (2, 3)]),
        ([0, 0, 1, 1, 0, 0], [(0, 1), (2, 3), (4, 5)]),
        ([0, 1, 1, 1, 1, 0], [(1, 4)]),
    ]

    for test in tests:
        assert util.get_contiguous_ranges(test[TEST], 0, len(test[0])) == test[ANSWER]


def test_convert(creds_json, sa_config_json):
    oauth = OAuth2Credentials.from_json(json.dumps(creds_json))
    sa = ServiceAccountCredentials.from_json_keyfile_dict(sa_config_json)

    assert isinstance(util.convert_credentials(oauth), credentials.Credentials)
    assert isinstance(util.convert_credentials(sa), service_account.Credentials)


def test_parse_permissions():
    tests = [
        (
            "aiguo.fernandez@gmail.com",
            {
                "value": "aiguo.fernandez@gmail.com",
                "perm_type": "user",
                "role": "reader",
            },
        ),
        (
            "aiguofer.com|owner",
            {"value": "aiguofer.com", "perm_type": "domain", "role": "owner"},
        ),
        ("anyone|writer", {"perm_type": "anyone", "role": "writer"}),
        (
            "difernan@redhat.com|no",
            {
                "value": "difernan@redhat.com",
                "perm_type": "user",
                "role": "reader",
                "notify": False,
            },
        ),
        ("anyone|link", {"perm_type": "anyone", "role": "reader", "with_link": True}),
    ]

    for test in tests:
        assert util.parse_permission(test[TEST]) == test[ANSWER]


def test_remove_keys():
    tests = [
        ([{}], {}),
        ([{}, ["stuff"]], {}),
        ([{"foo": "bar", "bar": "foo"}, ["foo"]], {"bar": "foo"}),
        ([{"foo": "bar", "bar": "foo"}, ["foo", "bar"]], {}),
        ([{"foo": "bar", "bar": "foo"}], {"foo": "bar", "bar": "foo"}),
        ([{"foo": "bar", "bar": "foo"}, ["doesntexist"]], {"foo": "bar", "bar": "foo"}),
    ]

    for test in tests:
        assert util.remove_keys(*test[TEST]) == test[ANSWER]


def test_remove_keys_from_list():
    tests = [
        (
            [[{"foo": "bar", "bar": "foo"}, {"foo": "fighter"}], ["foo"]],
            [{"bar": "foo"}, {}],
        ),
        (
            [[{"foo": "bar", "bar": "foo"}, {"foo": "fighter"}], ["bar"]],
            [{"foo": "bar"}, {"foo": "fighter"}],
        ),
        ([[], ["foo", "bar"]], []),
        ([[]], []),
    ]

    for test in tests:
        assert util.remove_keys_from_list(*test[TEST]) == test[ANSWER]


def test_add_paths():
    tests = [
        (
            [
                {"id": "root"},
                [
                    {"id": "1", "name": "sub", "parents": ["root"]},
                    {"id": "2", "name": "subsub", "parents": ["1"]},
                    {"id": "3", "name": "sub1", "parents": ["root"]},
                    {"id": "4", "name": "subsubsub", "parents": ["2"]},
                ],
            ],
            [
                {"id": "1", "name": "sub", "parents": ["root"], "path": "/sub"},
                {"id": "2", "name": "subsub", "parents": ["1"], "path": "/sub/subsub"},
                {"id": "3", "name": "sub1", "parents": ["root"], "path": "/sub1"},
                {
                    "id": "4",
                    "name": "subsubsub",
                    "parents": ["2"],
                    "path": "/sub/subsub/subsubsub",
                },
            ],
        )
    ]

    for test in tests:
        util.add_paths(*test[TEST])
        assert test[TEST][1] == test[ANSWER]


def test_folders_to_create():
    dirs = [
        {"id": "1", "name": "sub", "parents": ["root"], "path": "/sub"},
        {"id": "2", "name": "subsub", "parents": ["1"], "path": "/sub/subsub"},
        {"id": "3", "name": "sub1", "parents": ["root"], "path": "/sub1"},
        {
            "id": "4",
            "name": "subsubsub",
            "parents": ["2"],
            "path": "/sub/subsub/subsubsub",
        },
    ]

    tests = [
        ("/does/not/exist", ({"id": "root"}, ["does", "not", "exist"])),
        ("/sub/does/not/exist", (dirs[0], ["does", "not", "exist"])),
        ("/sub/subsub", (dirs[1], [])),
    ]

    for test in tests:
        assert util.folders_to_create(test[TEST], dirs) == test[ANSWER]
