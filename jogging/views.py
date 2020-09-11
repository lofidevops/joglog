# jogging/views.py

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import generics
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from .logic import CUSTOM_FILTER_OPERATORS, evaluate_custom_filter
from .models import JoggingSession
from .permissions import UserRolePermissions, is_anonymous_or_simply_staff
from .serializers import JoggingSessionSerializer, UserSerializer


# == API root ==


@api_view(["GET"])
def api_root(request):
    return Response(
        {
            "users": reverse("user-list", request=request),
            "sessions": reverse("session-list", request=request),
            "report": reverse("report-list", request=request),
        }
    )


# == Sessions ==


@api_view(["GET", "DELETE", "PUT"])
def get_delete_update_session(request, id):

    if is_anonymous_or_simply_staff(request):
        return Response(status=status.HTTP_403_FORBIDDEN)

    # Get session by ID
    try:
        session = JoggingSession.objects.get(id=id)
    except JoggingSession.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # Only owners and superusers can modify a record
    is_owner = session.user.id == request.user.id
    if not is_owner and not request.user.is_superuser:
        return Response(status=status.HTTP_403_FORBIDDEN)

    # Get single session
    if request.method == "GET":
        serializer = JoggingSessionSerializer(session, context={"request": request})
        return Response(serializer.data)

    # Delete single session
    elif request.method == "DELETE":
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Update single session
    elif request.method == "PUT":

        serializer = JoggingSessionSerializer(
            session, data=request.data, context={"request": request}
        )

        try:
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)
        except ValidationError:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
def get_post_sessions(request):

    if is_anonymous_or_simply_staff(request):
        return Response(status=status.HTTP_403_FORBIDDEN)

    filter_string = request.query_params.get("filter", None)

    # Get all sessions
    if request.method == "GET":

        # Get all sessions (apply user filter if required)
        kwargs = {}

        if not request.user.is_superuser:
            kwargs["user"] = request.user

        all_records_by_name = JoggingSession.objects.filter(**kwargs)

        # Apply custom filter
        if filter_string is not None and filter_string != "":
            ids = [
                session.id
                for session in all_records_by_name
                if apply_custom_session_filter(session, filter_string)
            ]

            all_records_by_name = JoggingSession.objects.filter(
                id__in=ids
            )  # queryset with all sessions that matched the filter

        # Serialize and return the results
        serializer = JoggingSessionSerializer(
            all_records_by_name, many=True, context={"request": request}
        )

        return Response(serializer.data)

    # Insert new session
    elif request.method == "POST":

        # Validate permissions
        if request.data.get("user") is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        user_id = int(request.data.get("user"))
        if not request.user.is_superuser and request.user.id != user_id:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        # Create input data
        data = {}
        user = None

        try:
            user = get_user_model().objects.get(id=user_id)
            data["duration"] = int(request.data.get("duration"))
            data["distance"] = int(request.data.get("distance"))
            data["lu_weather_location"] = str(request.data.get("lu_weather_location"))
            data["start"] = datetime.fromisoformat(request.data.get("start"))
        except BaseException:
            pass  # data will fail in serialization

        # Store serialized data
        serializer = JoggingSessionSerializer(data=data, context={"request": request})
        if serializer.is_valid():

            try:
                serializer.save(user=user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def apply_custom_session_filter(session, custom_filter):

    session_tokens = CUSTOM_FILTER_OPERATORS.copy()
    session_tokens["start"] = "'" + str(session.start.strftime("%Y-%m-%dT%H:%M")) + "'"
    session_tokens["dn_week"] = str(session.dn_week)
    session_tokens["local_timezone"] = "'" + str(session.local_timezone) + "'"
    session_tokens["distance"] = str(session.distance)
    session_tokens["duration"] = str(session.duration)
    session_tokens["speed"] = str(session.dn_speed)
    session_tokens["lu_weather_location"] = "'" + str(session.lu_weather_location) + "'"
    session_tokens["lu_weather"] = "'" + str(session.lu_weather) + "'"
    session_tokens["user"] = str(session.user.id)

    return evaluate_custom_filter(custom_filter, session_tokens)


# == Users ==


class UserList(generics.ListCreateAPIView):
    queryset = get_user_model().objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = (UserRolePermissions,)
    filter = None

    @classmethod
    def apply_custom_filter(cls, user, custom_filter):
        user_tokens = CUSTOM_FILTER_OPERATORS.copy()

        user_tokens["username"] = "'" + user.username + "'"

        if user.is_superuser:
            role = "superuser"
        elif user.is_staff:
            role = "staff"
        else:
            role = "jogger"

        user_tokens["role"] = "'" + role + "'"

        return evaluate_custom_filter(custom_filter, user_tokens)

    def get_queryset(self):

        custom_filter = self.request.query_params.get("filter", None)

        if custom_filter is not None:
            users = get_user_model().objects.all().order_by("username")
            ids = [
                user.id
                for user in users
                if self.apply_custom_filter(user, custom_filter)
            ]

            return users.filter(
                id__in=ids
            )  # queryset with all users that matched the filter
        else:
            return super(UserList, self).get_queryset()


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = get_user_model().objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = (UserRolePermissions,)


# == Reports ==


class ReportList(APIView):
    filter = None

    def get(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)

        custom_filter = self.request.query_params.get("filter", None)

        if request.user.is_staff or request.user.is_superuser:
            result = JoggingSession.generate_user_report(None, custom_filter)
        else:
            user_id = request.user.id
            result = JoggingSession.generate_user_report(user_id, custom_filter)

        return Response(result, status=status.HTTP_200_OK)
