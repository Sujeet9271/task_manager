from rest_framework import permissions

class IsBoardMemberOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Read-only for non-members
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user in obj.members.all() or request.user == obj.created_by