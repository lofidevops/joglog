import pytest
from .logic import (
    _minimal_token_whitespace,
    _replace_tokens,
    evaluate_custom_filter,
    get_weather,
)


@pytest.mark.parametrize(
    "input_string",
    ["(test)", "( test )", " ( test ) ", "(  test  )", "  (       test     )   "],
)
def test_whitespace_management(input_string):

    assert _minimal_token_whitespace(input_string) == "( test )"


TEST_REPLACEMENTS = {"eq": "==", "ne": "!="}


@pytest.mark.parametrize(
    "raw_string,replacements,target", [("2 ne 3", TEST_REPLACEMENTS, "2 != 3")]
)
def test_token_population(raw_string, replacements, target):

    raw_list = raw_string.split()
    result = " ".join(_replace_tokens(raw_list, replacements))
    assert result == target


@pytest.mark.parametrize(
    "raw_string,replacements,target", [("2 ne 3", TEST_REPLACEMENTS, True)]
)
def test_token_evaluation(raw_string, replacements, target):

    assert evaluate_custom_filter(raw_string, replacements) is target


@pytest.mark.parametrize(
    "location,iso_timestamp,target",
    [
        (None, "2010-10-10T10:10:10+00:00", ""),
        ("", "2010-10-10T10:10:10+00:00", ""),
        ("sdfhsdfhsdkfjhdskfhd", "2010-10-10T10:10:10+00:00", ""),
        ("London,UK", "sdfjkhsdkfhdkf", ""),
        ("London,UK", "2010-10-10T10:10:10+00:00", "NOTBLANK"),
    ],
)
def test_get_weather(location, iso_timestamp, target):

    if target == "":
        assert get_weather(location, iso_timestamp) == ""
    else:
        assert get_weather(location, iso_timestamp) != ""
