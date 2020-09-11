from django.contrib import admin

from .models import JoggingSession


class JoggingSessionAdmin(admin.ModelAdmin):
    fields = (
        "user",
        "start",
        "local_timezone",
        "dn_week",
        "distance",
        "duration",
        "dn_speed",
        "lu_weather_location",
        "lu_weather",
    )
    readonly_fields = ("dn_week", "dn_speed", "lu_weather")


admin.site.register(JoggingSession, JoggingSessionAdmin)
