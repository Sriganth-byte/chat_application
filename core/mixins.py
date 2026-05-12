"""
Reusable view mixins.
"""
from rest_framework.response import Response
from rest_framework import status


class MultiSerializerMixin:
    """
    Allows different serializers for different actions.
    Define attribute: `serializer_classes` as a dict mapping action -> serializer.
    """
    serializer_classes = {}

    def get_serializer_class(self):
        return self.serializer_classes.get(
            self.action,
            self.serializer_class
        )


class BulkCreateMixin:
    """
    Mixin to handle bulk creation of objects.
    """
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_bulk_create(self, serializer):
        serializer.save()


class BulkUpdateMixin:
    """
    Mixin to handle bulk updates.
    """
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instances = self.get_objects()
        serializer = self.get_serializer(
            instances,
            data=request.data,
            partial=partial,
            many=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_bulk_update(serializer)
        return Response(serializer.data)

    def get_objects(self):
        raise NotImplementedError("Must implement get_objects method")

    def perform_bulk_update(self, serializer):
        serializer.save()
