# jogging/logic.py

import random

import requests
from django.conf import settings


# == Custom filters ==


CUSTOM_FILTER_OPERATORS = {
    "eq": "==",
    "ne": "!=",
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
    "(": "(",
    ")": ")",
}


def _minimal_token_whitespace(raw_string):
    """
    Buffer tokens with minimal whitespace. This makes splitting easy.
    """

    # Add buffer around brackets
    raw_string = raw_string.replace("(", " ( ").replace(")", " ) ").strip()

    # Reduce extraneous whitespace
    while "  " in raw_string:
        raw_string = raw_string.replace("  ", " ")

    return raw_string


def _replace_tokens(token_list, replacement_map):
    """Replace tokens with values from the replacement map, if they exist."""

    new_statement = []
    for token in token_list:
        new_statement.append(
            replacement_map.get(token, str(token))
        )  # if token is not recognised, use it as a value

    return new_statement


def _populate_tokens(unpopulated_string, replacement_map):
    """Populate a string with tokens from the replacement map."""

    unpopulated_tokens = _minimal_token_whitespace(unpopulated_string).split()
    new_tokens = _replace_tokens(unpopulated_tokens, replacement_map)
    return " ".join(new_tokens)


def evaluate_custom_filter(filter_string, replacement_map):

    new_statement = _populate_tokens(filter_string, replacement_map)
    # evaluate final statement
    try:
        return eval(new_statement)
    except BaseException:
        return False


# == Weather ==


def get_weather(location, iso_timestamp):
    """
    Get the recorded weather for this location and timestamp. If the value
    cannot be retrieved for any reason, return an empty string.
    """

    if location is None or location == "":
        return ""

    try:
        return _get_weather_unsafe(location, iso_timestamp)
    except BaseException as e:
        print("Weather results failed: %s" % e)

        # in the debug environment, work around weather failures so we get nice results
        if settings.DEBUG:
            print("Generating random weather." % e)
            random.seed(location + iso_timestamp)  # input-based seed for stable results
            return random.choice(["CLEAR", "CLEAR", "CLOUDY", "PRECIPITATION"])
        else:
            return ""


def _get_weather_unsafe(location, iso_timestamp):
    """
    Query the weather.visualcrossing.com API for the recorded weather
    for this location and timestamp. Exceptions are not caught.
    """

    # Construct query for weather.visualcrossing.com API

    timestamp = iso_timestamp[:-6]  # remove +00:00 (6 characters) from the end

    path_parts = [
        "http://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/weatherdata/history?goal=history",
        "aggregateHours=24",
        "startDateTime={timestamp}",
        "endDateTime={timestamp}",
        "contentType=json",
        "unitGroup=metric",
        "locations={location}",
        "key={key}",
    ]

    value_parts = {
        "timestamp": timestamp,
        "location": location,
        "key": settings.WEATHER_API_KEY,
    }

    # Perform query and extract conditions

    try:
        query_url = "&".join(path_parts).format(**value_parts)
        result = requests.get(query_url).json()
        conditions = result["locations"][location]["values"][0]["conditions"].lower()
    except BaseException as e:
        known_error = result["errorCode"] is not None and result["message"] is not None
        if known_error and result["message"].endswith("could not be found"):
            return ""  # return blank for unknown locations
        elif known_error:
            message = result["message"]
        else:
            message = str(e)  # raise any other problems

        raise ValueError(message)

    # Return simplified condition summary

    summary = "OTHER"
    summary_options = {
        "CLEAR": ["sun", "clear"],
        "CLOUDY": ["cloud", "overcast"],
        "PRECIPITATION": ["rain", "shower", "storm", "thunder", "snow", "hail"],
    }

    for key in summary_options.keys():
        for value in summary_options[key]:
            if value in conditions:
                summary = key

    return summary
