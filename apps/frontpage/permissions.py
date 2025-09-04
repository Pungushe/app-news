from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Пользовательское разрешение, позволяющее только автору объекта редактировать его.
    """

    def has_object_permission(self, request, view, obj):
        # Разрешения на чтение разрешены для любого запроса,
        # поэтому мы всегда разрешаем запросы GET, HEAD или OPTIONS.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Разрешения на запись разрешены только автору поста.
        return obj.author == request.user