import json

from django.urls import reverse
from rest_framework import status

from .common_test import *
from .models import JoggingSession
from .serializers import JoggingSessionSerializer
from .views import apply_custom_session_filter, UserList

# Details used when inserting data via REST

PARTIAL_SESSION = {
    "user": None,
    "duration": 60,
    "distance": 1000,
    "start": SAMPLE_TIMESTAMP,
    "lu_weather_location": "London,UK",
}

# Details used when creating new users

NEW_SUPERUSER_DETAILS = {
    "username": "superuser2",
    "password": "********",
    "is_superuser": True,
    "is_staff": True,
}

NEW_STAFF_DETAILS = {
    "username": "staff2",
    "password": "********",
    "is_superuser": False,
    "is_staff": True,
}

NEW_JOGGER_DETAILS = {
    "username": "jogger2",
    "password": "********",
    "is_superuser": False,
    "is_staff": False,
}


# Session tests


@pytest.mark.parametrize(
    "role,response_status",
    [
        ("superuser", status.HTTP_200_OK),
        ("staff", status.HTTP_200_OK),
        ("jogger", status.HTTP_200_OK),
        ("anonymous", status.HTTP_200_OK),
    ],
)
@pytest.mark.django_db
def test_root_request(api_client, role, response_status):
    url = reverse("api_root")
    response = api_client(role).get(url)
    assert response.status_code == response_status


@pytest.mark.django_db
def test_get_all_by_superuser(populate_samples, api_client, generate_request):

    populate_samples
    client = api_client("superuser")
    request = generate_request("superuser")

    # Get data directly
    all_records = JoggingSession.objects.all()
    serializer = JoggingSessionSerializer(
        all_records, many=True, context={"request": request}
    )

    # Get data through API
    response = client.get(reverse("session-list"))

    # Validate results
    assert response.status_code == status.HTTP_200_OK
    assert serializer.data == response.data


@pytest.mark.parametrize(
    "role,response_status",
    [
        ("superuser", status.HTTP_200_OK),
        ("staff", status.HTTP_403_FORBIDDEN),
        ("jogger", status.HTTP_200_OK),
        ("anonymous", status.HTTP_403_FORBIDDEN),
    ],
)
@pytest.mark.django_db
def test_basic_session_request(api_client, role, response_status):
    url = reverse("session-list")
    response = api_client(role).get(url)
    assert response.status_code == response_status


def test_filtered_session_request(api_client):

    filter_string = "speed eq 0"
    response = api_client("superuser").get(
        reverse("session-list") + "?filter=" + filter_string
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_get_all_by_jogger(populate_samples, api_client, generate_request):

    populate_samples
    client = api_client("jogger")
    request = generate_request("jogger")

    # Get data directly
    all_records_by_name = JoggingSession.objects.filter(user__username=JOGGER_NAME)
    serializer = JoggingSessionSerializer(
        all_records_by_name, many=True, context={"request": request}
    )

    # Get data through API
    response = client.get(reverse("session-list"))

    # Validate results
    assert response.status_code == status.HTTP_200_OK
    assert serializer.data == response.data


@pytest.mark.parametrize(
    "role,username,response_status",
    [
        ("superuser", SAMPLE_NAME, status.HTTP_200_OK),
        ("staff", SAMPLE_NAME, status.HTTP_403_FORBIDDEN),
        ("jogger", JOGGER_NAME, status.HTTP_200_OK),  # can retrieve own data
        (
            "jogger",
            SAMPLE_NAME,
            status.HTTP_403_FORBIDDEN,
        ),  # cannot retrieve other data
        ("anonymous", SAMPLE_NAME, status.HTTP_403_FORBIDDEN),
    ],
)
@pytest.mark.django_db
def test_get_single_session(
    populate_samples,
    get_existing_session,
    api_client,
    generate_request,
    role,
    username,
    response_status,
):

    # Populate and get primary key
    populate_samples  # call fixture
    sample = get_existing_session(username, SAMPLE_TIMESTAMP)
    sample_id = sample.id

    client = api_client(role)
    request = generate_request(role)

    # Get serialized data
    record = JoggingSession.objects.get(id=sample_id)
    serializer = JoggingSessionSerializer(record, context={"request": request})

    # Get API response
    response = client.get(reverse("session-detail", kwargs={"id": sample.id}))

    # Validate results
    assert response.status_code == response_status

    if response_status == status.HTTP_200_OK:
        assert serializer.data == response.data
    else:
        assert serializer.data != response.data


@pytest.mark.django_db
def test_get_single_session_with_invalid_id(api_client, populate_samples):

    populate_samples  # call fixture
    response = api_client("jogger").get(reverse("session-detail", kwargs={"id": 999}))
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "role,username,response_status",
    [
        ("superuser", SAMPLE_NAME, status.HTTP_201_CREATED),
        ("staff", SAMPLE_NAME, status.HTTP_403_FORBIDDEN),
        ("jogger", JOGGER_NAME, status.HTTP_201_CREATED),  # can post own data
        ("jogger", SAMPLE_NAME, status.HTTP_401_UNAUTHORIZED),  # cannot post other data
        ("anonymous", SAMPLE_NAME, status.HTTP_403_FORBIDDEN),
    ],
)
@pytest.mark.django_db
def test_post_valid_session(
    api_client, create_or_get_user, role, username, response_status
):

    user = create_or_get_user(username)
    session = PARTIAL_SESSION.copy()
    session["user"] = user.id

    response = api_client(role).post(
        reverse("session-list"),
        data=json.dumps(session),
        content_type="application/json",
    )

    assert response.status_code == response_status


@pytest.mark.django_db
def test_post_invalid_session(api_client, create_or_get_user):
    """
    Confirm that the system rejects invalid sessions. We do not consider all
    forms of validity, these are covered by the unit tests on the
    JoggingSession model.
    """

    user = create_or_get_user(JOGGER_NAME)
    session = PARTIAL_SESSION.copy()
    session["user"] = user.id
    session["distance"] = -1  # bad distance

    response = api_client("jogger").post(
        reverse("session-list"),
        data=json.dumps(session),
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    "role,username,new_distance,response_status",
    [
        ("superuser", SAMPLE_NAME, 2000, status.HTTP_204_NO_CONTENT),
        (
            "superuser",
            SAMPLE_NAME,
            -100,
            status.HTTP_400_BAD_REQUEST,
        ),  # has permission but invalid
        ("staff", SAMPLE_NAME, 2000, status.HTTP_403_FORBIDDEN),
        (
            "jogger",
            JOGGER_NAME,
            2000,
            status.HTTP_204_NO_CONTENT,
        ),  # can update own data
        (
            "jogger",
            JOGGER_NAME,
            -100,
            status.HTTP_400_BAD_REQUEST,
        ),  # has permission but invalid
        (
            "jogger",
            SAMPLE_NAME,
            2000,
            status.HTTP_403_FORBIDDEN,
        ),  # cannot update other data
        ("anonymous", SAMPLE_NAME, 2000, status.HTTP_403_FORBIDDEN),
    ],
)
@pytest.mark.django_db
def test_put_update(
    api_client,
    populate_samples,
    get_existing_session,
    role,
    username,
    new_distance,
    response_status,
):

    populate_samples
    sample = get_existing_session(username, SAMPLE_TIMESTAMP)
    assert sample.distance != new_distance

    new_data = {
        "user": sample.user.id,
        "duration": sample.duration,
        "distance": new_distance,  # minor change
        "start": SAMPLE_INPUT_TIMESTAMP,  # alternate formatting for SAMPLE_TIMESTAMP
    }

    # Get API response
    response = api_client(role).put(
        reverse("session-detail", kwargs={"id": sample.id}),
        data=json.dumps(new_data),
        content_type="application/json",
    )

    # Validate results
    assert response.status_code == response_status

    # Confirm that original session is the only session stored
    # and has been updated / not updated
    new_sample = get_existing_session(username, SAMPLE_TIMESTAMP)

    if response_status == status.HTTP_204_NO_CONTENT:
        assert new_sample.distance == new_distance
    else:
        assert new_sample.distance != new_distance


@pytest.mark.parametrize(
    "role,username,response_status",
    [
        ("superuser", SAMPLE_NAME, status.HTTP_204_NO_CONTENT),
        ("staff", SAMPLE_NAME, status.HTTP_403_FORBIDDEN),
        ("jogger", JOGGER_NAME, status.HTTP_204_NO_CONTENT),  # can delete own data
        ("jogger", SAMPLE_NAME, status.HTTP_403_FORBIDDEN),  # cannot delete other data
        ("anonymous", SAMPLE_NAME, status.HTTP_403_FORBIDDEN),
    ],
)
@pytest.mark.django_db
def test_delete_valid_session(
    api_client, populate_samples, get_existing_session, role, username, response_status
):

    populate_samples  # this calls the fixture method
    sample = get_existing_session(username, SAMPLE_TIMESTAMP)

    response = api_client(role).delete(
        reverse("session-detail", kwargs={"id": sample.id})
    )

    assert response.status_code == response_status

    # Confirm sample deleted successfully / not deleted
    if response_status == status.HTTP_204_NO_CONTENT:
        with pytest.raises(JoggingSession.DoesNotExist):
            get_existing_session(username, SAMPLE_TIMESTAMP)
    else:
        get_existing_session(username, SAMPLE_TIMESTAMP)


@pytest.mark.django_db
def test_delete_invalid_session(api_client):

    populate_samples  # this calls the fixture method

    response = api_client("jogger").delete(
        reverse("session-detail", kwargs={"id": 999})  # non-existent session
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


# == Users ==


@pytest.mark.parametrize(
    "role,response_status",
    [
        ("superuser", status.HTTP_200_OK),
        ("staff", status.HTTP_200_OK),
        ("jogger", status.HTTP_200_OK),
        ("anonymous", status.HTTP_200_OK),
    ],
)
@pytest.mark.django_db
def test_basic_user_request(api_client, role, response_status):
    url = reverse("user-list")
    response = api_client(role).get(url)
    assert response.status_code == response_status


def test_filtered_user_request(api_client):

    filter_string = "username eq '" + SAMPLE_NAME + "'"
    response = api_client("superuser").get(
        reverse("user-list") + "?filter=" + filter_string
    )
    assert response.status_code == status.HTTP_200_OK


def idfn_create_or_get_user(val):
    """Generate helpful display value for user tests."""
    if isinstance(val, (dict,)) and "username" in val.keys():
        return val["username"]


@pytest.mark.parametrize(
    "role,details,response_status",
    [
        (
            "superuser",
            NEW_SUPERUSER_DETAILS,
            status.HTTP_201_CREATED,
        ),  # can create superuser
        ("superuser", NEW_STAFF_DETAILS, status.HTTP_201_CREATED),  # can create staff
        ("superuser", NEW_JOGGER_DETAILS, status.HTTP_201_CREATED),  # can create jogger
        ("staff", NEW_SUPERUSER_DETAILS, status.HTTP_403_FORBIDDEN),
        ("staff", NEW_STAFF_DETAILS, status.HTTP_403_FORBIDDEN),
        ("staff", NEW_JOGGER_DETAILS, status.HTTP_201_CREATED),  # can create jogger
        ("jogger", NEW_SUPERUSER_DETAILS, status.HTTP_403_FORBIDDEN),
        ("jogger", NEW_STAFF_DETAILS, status.HTTP_403_FORBIDDEN),
        ("jogger", NEW_JOGGER_DETAILS, status.HTTP_403_FORBIDDEN),
        ("anonymous", NEW_SUPERUSER_DETAILS, status.HTTP_403_FORBIDDEN),
        ("anonymous", NEW_STAFF_DETAILS, status.HTTP_403_FORBIDDEN),
        ("anonymous", NEW_JOGGER_DETAILS, status.HTTP_201_CREATED),
    ],
    ids=idfn_create_or_get_user,
)
@pytest.mark.django_db
def test_create_user(api_client, role, details, response_status):

    response = api_client(role).post(
        reverse("user-list"), data=json.dumps(details), content_type="application/json"
    )

    assert response.status_code == response_status


@pytest.mark.parametrize(
    "role,target,response_status",
    [
        ("superuser", SUPERUSER_NAME, status.HTTP_200_OK),  # can update self
        ("superuser", "test_superuser", status.HTTP_200_OK),  # can update superuser
        ("superuser", "test_staff", status.HTTP_200_OK),  # can update staff
        ("superuser", "test_jogger", status.HTTP_200_OK),  # can update jogger
        ("staff", STAFF_NAME, status.HTTP_200_OK),  # can update self
        ("staff", "test_superuser", status.HTTP_403_FORBIDDEN),
        ("staff", "test_staff", status.HTTP_403_FORBIDDEN),
        ("staff", "test_jogger", status.HTTP_200_OK),  # can update jogger
        ("jogger", JOGGER_NAME, status.HTTP_200_OK),  # can update self
        ("jogger", "test_superuser", status.HTTP_403_FORBIDDEN),
        ("jogger", "test_staff", status.HTTP_403_FORBIDDEN),
        ("jogger", "test_jogger", status.HTTP_403_FORBIDDEN),
        ("anonymous", "test_superuser", status.HTTP_403_FORBIDDEN),
        ("anonymous", "test_staff", status.HTTP_403_FORBIDDEN),
        ("anonymous", "test_jogger", status.HTTP_403_FORBIDDEN),
    ],
)
@pytest.mark.django_db
def test_update_user(
    populate_users, create_or_get_user, api_client, role, target, response_status
):

    populate_users
    user = create_or_get_user(target)

    updated_data = {
        "username": user.username,
        "password": "!!!!!!!!!!",  # new password
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }

    # Get API response
    response = api_client(role).put(
        reverse("user-detail", kwargs={"pk": user.pk}),
        data=json.dumps(updated_data),
        content_type="application/json",
    )

    # Validate results
    assert response.status_code == response_status


# Report and filter tests


@pytest.mark.parametrize(
    "role,response_status",
    [
        ("superuser", status.HTTP_200_OK),
        ("staff", status.HTTP_200_OK),
        ("jogger", status.HTTP_200_OK),
        ("anonymous", status.HTTP_403_FORBIDDEN),
    ],
)
@pytest.mark.django_db
def test_basic_report_request(api_client, role, response_status):
    url = reverse("report-list")
    response = api_client(role).get(url)
    assert response.status_code == response_status


def test_filtered_report_request(api_client):

    filter_string = "week eq 202052"
    response = api_client("superuser").get(
        reverse("session-list") + "?filter=" + filter_string
    )
    assert response.status_code == status.HTTP_200_OK


FULL_RESULT = {
    1: {
        "avg_speed": 1.0,
        "distance": 3000,
        "duration": 180,
        "record": 1,
        "user": 1,
        "week": 202008,
    },
    2: {
        "avg_speed": 1.0,
        "distance": 3000,
        "duration": 180,
        "record": 2,
        "user": 2,
        "week": 202008,
    },
}

FILTER = "user ne 1"

FILTERED_RESULT = {
    2: {
        "avg_speed": 1.0,
        "distance": 3000,
        "duration": 180,
        "record": 2,
        "user": 2,
        "week": 202008,
    }
}

JOGGER_RESULT = {
    1: {
        "avg_speed": 1.0,
        "distance": 3000,
        "duration": 180,
        "record": 1,
        "user": 2,
        "week": 202008,
    }
}

FILTERED_JOGGER_RESULT = {
    1: {
        "avg_speed": 1.0,
        "distance": 3000,
        "duration": 180,
        "record": 1,
        "user": 2,
        "week": 202008,
    }
}

FILTER_B = "user ne 2"

FILTERED_JOGGER_RESULT_B = {}


@pytest.mark.parametrize(
    "username,report_filter,target",
    [
        (None, None, FULL_RESULT),
        (None, FILTER, FILTERED_RESULT),
        (JOGGER_NAME, None, JOGGER_RESULT),
        (JOGGER_NAME, FILTER, FILTERED_JOGGER_RESULT),
        (JOGGER_NAME, FILTER_B, FILTERED_JOGGER_RESULT_B),
    ],
)
@pytest.mark.django_db
def test_user_report(
    populate_samples, create_or_get_user, username, report_filter, target
):

    populate_samples

    if username is None:
        user_id = None
    else:
        user = create_or_get_user(username)
        user_id = user.id

    result = JoggingSession.generate_user_report(user_id, report_filter)
    assert result == target


@pytest.mark.parametrize(
    "filter_string,target",
    [
        ("speed lte 2", True),
        ("speed eq 1", True),
        ("speed gt 5", False),
        ("local_timezone ne 'Asia/Hong_Kong'", True),
        ("lu_weather_location ne 'Sydney,Australia'", True),
        ("lu_weather ne 'other'", True),
    ],
)
@pytest.mark.django_db
def test_filter_session(populate_samples, get_existing_session, filter_string, target):

    populate_samples
    session = get_existing_session(SAMPLE_NAME, SAMPLE_TIMESTAMP)

    assert apply_custom_session_filter(session, filter_string) == target


@pytest.mark.parametrize(
    "username,filter_string,target",
    [
        ("test_superuser", "role eq 'superuser'", True),
        ("test_superuser", "role eq 'staff'", False),
        ("test_superuser", "role eq 'jogger'", False),
        ("test_staff", "role eq 'superuser'", False),
        ("test_staff", "role eq 'staff'", True),
        ("test_staff", "role eq 'jogger'", False),
        ("test_jogger", "role eq 'superuser'", False),
        ("test_jogger", "role eq 'staff'", False),
        ("test_jogger", "role eq 'jogger'", True),
    ],
)
def test_filter_user(
    populate_users, create_or_get_user, username, filter_string, target
):

    populate_users
    user = create_or_get_user(username)
    assert UserList.apply_custom_filter(user, filter_string) == target
