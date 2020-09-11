# jogging/models.py

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from .logic import get_weather, evaluate_custom_filter, CUSTOM_FILTER_OPERATORS


# == Sessions ==


class JoggingSession(models.Model):
    """
    A jogging session is defined for a particular user on a particular day. Speed and
    calendar week are calculated and stored for convenience. Local weather is recorded
    if possible. Users may optionally declare the local timezone.
    """

    distance = models.IntegerField("distance (meters)")
    dn_speed = models.DecimalField(
        "calculated speed (km/h)",
        editable=False,
        decimal_places=1,
        max_digits=3,
        default=0,
    )  # maximum speed 99.9 km/h, well above human limits
    dn_week = models.IntegerField(
        "calendar week (yyyyww)", editable=False, default=0
    )  # ISO 8601, YYYYWW format
    duration = models.IntegerField("duration (minutes)")
    local_timezone = models.TextField("local timezone (tzdb)", blank=True)
    lu_weather = models.TextField("weather", editable=False, blank=True)
    lu_weather_location = models.TextField(
        "location (for weather)", default="", blank=True
    )
    start = models.DateTimeField("start time (UTC)")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="jogging_sessions",
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ("-start", "id")

    def __str__(self):
        return "%s %s" % (self.user, self.start.isoformat()[:-9])

    def validate_unique(self, exclude=None):

        if not hasattr(self, "start") or self.start is None:
            raise ValidationError("Start time not defined.")

        if not hasattr(self, "user") or self.user is None:
            raise ValidationError("User not defined.")

        existing_sessions = JoggingSession.objects.exclude(id=self.id).filter(
            start__year=self.start.year,
            start__month=self.start.month,
            start__day=self.start.day,
            user=self.user,
        )  # NB this is a chained .exclude().filter()

        if len(existing_sessions) != 0:
            raise ValidationError("Another session already exists for this user+day.")

    def clean(self):
        """
        Validates value ranges, calculates denormalised values and requests missing lookup values.
        """

        # Validate distance
        if self.distance is None or self.distance < 0:
            raise ValidationError("Invalid distance value.")

        # Validate duration
        if self.duration is None or self.duration < 0:
            raise ValidationError("Invalid duration value.")

        # Validate timezone offset (zero offset == UTC)
        if self.start is None or self.start.tzinfo.utcoffset(self.start) != timedelta(
            0
        ):
            raise ValidationError("Timezone offset is not zero.")

        # Set speed
        if self.duration == 0:
            self.dn_speed = 0
        else:
            km = self.distance / 1000.0
            hr = self.duration / 60.0
            self.dn_speed = Decimal(km / hr).quantize(Decimal("1.0"))

        # Clean start time
        self.start = self.start.replace(second=0, microsecond=0)

        # Set calendar week
        iso_year, iso_week, iso_day = self.start.isocalendar()
        self.dn_week = (iso_year * 100) + iso_week

        # Look up weather
        if self.lu_weather == "" and self.lu_weather_location != "":
            self.lu_weather = get_weather(
                self.lu_weather_location, self.start.isoformat()
            )

    def save(self, *args, **kwargs):
        """
        Clean the object before saving. This is atypical in Django, but we perform
        lots of code-based, rather than form-based, manipulations.
        """

        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def generate_user_report(cls, user_id=None, custom_filter=None):

        # Filter by user if required
        kwargs = {}

        if user_id is not None:
            kwargs["user"] = get_user_model().objects.get(id=user_id)

        sessions = cls.objects.filter(**kwargs).order_by("-dn_week", "user", "-start")

        partial = {}

        # Collate items by user and week
        for item in sessions:
            dn_week = item.dn_week
            user_id = item.user.id
            collation_key = (dn_week, user_id)
            if collation_key not in partial.keys():
                partial[collation_key] = []

            partial[collation_key].append((item.distance, item.duration))

        # Calculate average user speed by week.
        # Note that this is total distance over total duration for recorded sessions,
        # so missing/skipped days do not reduce the average.
        calculation_result = {}
        record_id = 0
        for collation_key in partial.keys():
            dn_week, user_id = collation_key
            total_distance = 0
            total_duration = 0
            for distance, duration in partial[collation_key]:
                total_distance += distance
                total_duration += duration

            km = total_distance / 1000.0
            h = total_duration / 60.0
            speed = Decimal(km / h).quantize(Decimal("1.0"))

            record_id += 1
            calculation_result[record_id] = {
                "record": record_id,
                "user": user_id,
                "week": dn_week,
                "distance": total_distance,
                "duration": total_duration,
                "avg_speed": speed,
            }

        # If there is no custom filter, skip final pass
        if custom_filter is None:
            return calculation_result

        # Perform final pass
        final_result = {}
        for key, item in calculation_result.items():

            tokens = CUSTOM_FILTER_OPERATORS.copy()

            tokens["user"] = str(item["user"])
            tokens["week"] = str(item["week"])
            tokens["distance"] = str(item["distance"])
            tokens["duration"] = str(item["duration"])
            tokens["avg_speed"] = str(item["avg_speed"])

            if evaluate_custom_filter(custom_filter, tokens):
                final_result[key] = item.copy()

        return final_result
