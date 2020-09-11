# jogging/serializers.py

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import JoggingSession


# == Sessions ==


class JoggingSessionSerializer(serializers.HyperlinkedModelSerializer):

    url = serializers.HyperlinkedIdentityField(
        view_name="session-detail", lookup_field="id"
    )
    user = serializers.HyperlinkedRelatedField(
        view_name="user-detail", read_only=True, lookup_field="pk"
    )
    dn_week = serializers.ReadOnlyField()
    dn_speed = serializers.ReadOnlyField()
    lu_weather = serializers.ReadOnlyField()

    class Meta:
        model = JoggingSession
        fields = (
            "url",
            "start",
            "dn_week",
            "local_timezone",
            "distance",
            "duration",
            "dn_speed",
            "lu_weather_location",
            "lu_weather",
            "user",
        )


# == Users ==


class UserSerializer(serializers.HyperlinkedModelSerializer):
    jogging_sessions = serializers.HyperlinkedRelatedField(
        many=True, view_name="session-detail", read_only=True, lookup_field="id"
    )

    class Meta:
        model = get_user_model()
        fields = (
            "url",
            "username",
            "password",
            "is_staff",
            "is_superuser",
            "jogging_sessions",
        )

    def create(self, validated_data):
        instance = get_user_model().objects.create(**validated_data)
        instance.set_password(validated_data["password"])
        instance.save()
        return instance

    def update(self, instance, validated_data):
        instance.username = validated_data["username"]
        instance.is_staff = validated_data["is_staff"]
        instance.is_superuser = validated_data["is_superuser"]
        instance.set_password(validated_data["password"])
        instance.save()
        return instance
