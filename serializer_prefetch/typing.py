from __future__ import annotations
from django.db.models import Model, Prefetch

from typing import TYPE_CHECKING, Any, Generic, Iterable, Protocol, TypeVar, TypedDict

from rest_framework.serializers import BaseSerializer, Serializer


T = TypeVar("T", bound=Model)


class AdditionalSerializersTypedDict(TypedDict):
    serializer: SerializerWithMethods
    relation_and_field: str | Prefetch


class SerializerWithMethods(Serializer[T]):
    def get_select_related(self) -> Iterable[str]:
        return []

    def get_prefetch_related(self) -> Iterable[str | Prefetch]:
        return []

    def get_additional_serializers(self) -> Iterable[AdditionalSerializersTypedDict]:
        return []

    def get_force_prefetch(self) -> Iterable[str]:
        return []


if TYPE_CHECKING:

    class SerializerProtocol(Protocol, Generic[T]):
        def to_representation(
            self,
            instance: Model | Iterable[T] | dict[str, Any],
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            ...

        parent: BaseSerializer[T]

else:

    class SerializerProtocol(Generic[T]):
        ...
