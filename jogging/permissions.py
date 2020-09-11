# jogging/permissions.py

from rest_framework import permissions


def is_anonymous_or_simply_staff(request):

    if not request.user.is_authenticated:
        return True

    return request.user.is_staff and not request.user.is_superuser


# == Users ==


class UserRolePermissions(permissions.BasePermission):
    def has_permission(self, request, view):

        is_anonymous = not request.user.is_authenticated
        is_strictly_staff = request.user.is_staff and not request.user.is_superuser
        is_target_jogger = not request.data.get("is_staff") and not request.data.get(
            "is_superuser"
        )

        # superusers can perform all actions
        if request.user.is_superuser:
            return True
        # anonymous and staff may create joggers
        elif (
            request.method == "POST"
            and (is_anonymous or is_strictly_staff)
            and is_target_jogger
        ):
            return True
        # all other POST requests are invalid
        elif request.method == "POST":
            return False
        # all other requests are permitted or require object-level permission
        else:
            return True

    def has_object_permission(self, request, view, obj):

        # superusers can perform all actions
        if request.user.is_superuser:
            return True

        is_jogger_object = not obj.is_staff and not obj.is_superuser
        is_self = request.user.pk == obj.pk

        # staff can modify joggers
        if request.user.is_staff and is_jogger_object:
            return True
        # any user can modify their own record
        elif is_self:
            return True
        # all other cases are not permitted
        else:
            return False
