# jogging/jogging_test.py

from decimal import Decimal

from django.core.exceptions import ValidationError

from .common_test import *

VALID_START = "2020-02-19T11:01:20+00:00"
VALID_WEEK = 202008  # 19 February 2020 falls in calendar week 8 of 2020


@pytest.mark.django_db
def test_create_empty_session_fails():
    """
    A session with no values is invalid and cannot be created.
    """

    with pytest.raises(BaseException):
        JoggingSession.objects.create()


@pytest.mark.django_db
def test_create_and_delete_valid_session(create_session, delete_user_sessions):
    """
    A valid session can successfully save, pass checks and get deleted.
    """

    session = create_session(
        username="alice",
        duration=60,
        distance=1000,
        start_string=VALID_START,
        lu_weather_location="London,UK",
    )

    # Verify calculated values
    assert session.dn_speed == Decimal(1.0)  # 1000m in 60 mins = 1.0 km/hr
    assert session.start.second == 0  # cleaned
    assert session.start.microsecond == 0  # cleaned
    assert session.dn_week == VALID_WEEK  # correct
    assert (
        session.lu_weather is not None
    )  # confirms result stored, even if it's an API failure

    # Confirm delete method works
    delete_user_sessions("alice")


@pytest.mark.django_db
def test_create_session_with_invalid_duration(create_session):

    with pytest.raises(ValidationError):
        create_session(
            username="alice",
            duration=-1,
            distance=1000,
            start_string=VALID_START,
            lu_weather_location="London,UK",
        )


@pytest.mark.django_db
def test_create_session_with_bad_timezone(create_session):

    timestamp_with_bad_timezone = "2020-02-19T11:01:20+04:00"

    with pytest.raises(ValidationError):
        create_session(
            username="alice",
            duration=60,
            distance=1000,
            start_string=timestamp_with_bad_timezone,
            lu_weather_location="London,UK",
        )


@pytest.mark.django_db
def test_create_and_clean_session_with_invalid_distance(create_session):

    with pytest.raises(ValidationError):
        create_session(
            username="alice",
            duration=60,
            distance=-1,
            start_string=VALID_START,
            lu_weather_location="London,UK",
        )


@pytest.mark.django_db
def test_session_with_zero_duration_returns_zero_speed(create_session):

    session = create_session(
        username="alice",
        duration=0,
        distance=1000,
        start_string=VALID_START,
        lu_weather_location="London,UK",
    )
    assert session.dn_speed == 0


@pytest.mark.django_db
def test_session_with_unknown_location_returns_empty_weather(create_session):

    session = create_session(
        username="alice",
        duration=60,
        distance=1000,
        start_string=VALID_START,
        lu_weather_location="uqqygfdgdfgiuyeiruydfjfgeff",  # does not exist
    )
    assert session.lu_weather == ""


@pytest.mark.django_db
def test_two_records_on_the_same_day_are_not_allowed(
    create_session, get_existing_session
):

    # Confirm there are no pre-existing sessions
    assert JoggingSession.objects.filter(user__username="alice").count() == 0

    # Define two timestamps on the same UTC calendar day
    stamp1 = "2020-02-19T11:01:20+00:00"
    stamp2 = "2020-02-19T13:45:13+00:00"

    # Create record with first timestamp
    create_session(
        username="alice",
        duration=60,
        distance=1000,
        start_string=stamp1,
        lu_weather_location="London,UK",
    )

    # Confirm the attempt to create record with second timestamp fails
    with pytest.raises(ValidationError):
        create_session(
            username="alice",
            duration=60,
            distance=1000,
            start_string=stamp2,
            lu_weather_location="London,UK",
        )

    # Confirm that matching session is the only session stored
    get_existing_session("alice", stamp1)
