# jogging/common_test.py

from datetime import datetime, timedelta

import pytest
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from django.conf import settings

from .models import JoggingSession

SAMPLE_NAME = "alice"
SAMPLE_TIMESTAMP = "2020-02-19T11:00:00+00:00"
SAMPLE_INPUT_TIMESTAMP = "2020-02-19T11:00"  # alternate formatting for PUT test
JOGGER_NAME = "bob"
STAFF_NAME = "staff"
SUPERUSER_NAME = "superuser"


def test_debug_state():
    assert settings.DEBUG is not None  # ensure that settings have loaded


@pytest.fixture
def api_client(create_or_get_user):
    def _api_client(role):
        if role == "anonymous":
            return APIClient()

        elif role == "jogger":
            named_user = create_or_get_user(JOGGER_NAME)

        elif role == "staff":
            named_user = create_or_get_user(STAFF_NAME)
            named_user.is_staff = True
            named_user.is_superuser = False
            named_user.save()

        elif role == "superuser":
            named_user = create_or_get_user(STAFF_NAME)
            named_user.is_staff = True
            named_user.is_superuser = True
            named_user.save()

        else:
            raise ValueError("Role not recognised.")

        client = APIClient()
        client.force_authenticate(user=named_user)
        return client

    return _api_client


def test_bad_api_role(api_client):

    with pytest.raises(ValueError):
        api_client("unknown")


@pytest.fixture()
def generate_request(create_or_get_user):
    def _generate_request(role):

        factory = APIRequestFactory()
        request = factory.request()

        if role == "anonymous":
            return request

        elif role == "jogger":
            named_user = create_or_get_user(JOGGER_NAME)

        elif role == "staff":
            named_user = create_or_get_user(STAFF_NAME)
            named_user.is_staff = True
            named_user.is_superuser = False
            named_user.save()

        elif role == "superuser":
            named_user = create_or_get_user(STAFF_NAME)
            named_user.is_staff = True
            named_user.is_superuser = True
            named_user.save()

        else:
            raise ValueError("Role not recognised.")

        force_authenticate(request, named_user)
        return request

    return _generate_request


@pytest.fixture
def create_or_get_user(django_user_model):
    def _create_or_get_user(username):
        user, exists = django_user_model.objects.get_or_create(username=username)
        return user

    return _create_or_get_user


@pytest.fixture
def purge_all_sessions():
    JoggingSession.objects.all().delete()


@pytest.fixture
def create_session(django_user_model):
    def _create_session(
        username, start_string, duration, distance, lu_weather_location
    ):
        user, exists = django_user_model.objects.get_or_create(username=username)
        start_datetime = datetime.fromisoformat(start_string)

        return JoggingSession.objects.create(
            user=user,
            start=start_datetime,
            duration=duration,
            distance=distance,
            lu_weather_location=lu_weather_location,
        )

    return _create_session


@pytest.fixture
def delete_user_sessions(django_user_model):
    def delete_user_sessions_with_parameters(username):
        user = django_user_model.objects.get(username=username)
        user_id = user.id
        user.delete()
        session_count = JoggingSession.objects.filter(user__id=user_id).count()
        assert session_count == 0
        return True

    return delete_user_sessions_with_parameters


@pytest.fixture
def get_existing_session():
    def get_existing_session_with_parameters(username, timestamp_string):
        timestamp = datetime.fromisoformat(timestamp_string)
        return JoggingSession.objects.filter(
            start__year=timestamp.year,
            start__month=timestamp.month,
            start__day=timestamp.day,
            user__username=username,
        ).get()

    return get_existing_session_with_parameters


@pytest.fixture
def populate_samples(purge_all_sessions, create_session, get_existing_session):
    """Populate sample data. `get_existing_session` will now return a valid sample."""

    # Generate list of names
    namelist = [SAMPLE_NAME, JOGGER_NAME]

    # Generate list of timestamps
    timelist = []
    adjustments = [timedelta(days=-1), timedelta(days=0), timedelta(days=1)]
    for delta in adjustments:
        stamp = datetime.fromisoformat(SAMPLE_TIMESTAMP) + delta
        timelist.append(stamp.isoformat())

    # Create a valid session for every name/stamp combination
    for name in namelist:
        for stamp in timelist:
            create_session(
                username=name,
                duration=60,
                distance=1000,
                start_string=stamp,
                lu_weather_location="London,UK",
            )

    get_existing_session(SAMPLE_NAME, SAMPLE_TIMESTAMP)
    get_existing_session(JOGGER_NAME, SAMPLE_TIMESTAMP)


@pytest.fixture
def populate_users(create_or_get_user):

    test_jogger = create_or_get_user("test_jogger")
    test_jogger.set_password("????????")
    test_jogger.save()

    test_staff = create_or_get_user("test_staff")
    test_staff.set_password("????????")
    test_staff.is_staff = True
    test_staff.save()

    test_superuser = create_or_get_user("test_superuser")
    test_superuser.set_password("????????")
    test_superuser.is_staff = True
    test_superuser.is_superuser = True
    test_superuser.save()
