# jogging/urls.py

from django.urls import path

from . import views

urlpatterns = [
    path("", views.api_root, name="api_root"),
    path("api/v1/sessions/", views.get_post_sessions, name="session-list"),
    path(
        "api/v1/sessions/<int:id>",
        views.get_delete_update_session,
        name="session-detail",
    ),
    path("api/v1/users/", views.UserList.as_view(), name="user-list"),
    path("api/v1/users/<int:pk>/", views.UserDetail.as_view(), name="user-detail"),
    path("api/v1/report/", views.ReportList.as_view(), name="report-list"),
]
