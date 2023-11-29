from __future__ import annotations
from contextlib import suppress
import copy

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Model, Prefetch
from django.db.models.fields import Field as DjangoModelField
from django.db.models.fields.related import ForeignObjectRel

from serializer_prefetch.typing import SerializerWithMethods, T


def is_model_field(model: Model, source: str | Prefetch) -> bool:
    if hasattr(model, "_meta"):
        try:
            model_field = model._meta.get_field(
                source if isinstance(source, str) else source.prefetch_through
            )
            # This is how rest_framework does it
            if not isinstance(model_field, DjangoModelField | ForeignObjectRel):  # type: ignore
                return False
        except FieldDoesNotExist:
            return False

    return True


def join_prefetch(
    current_relation: Prefetch | str, item: Prefetch | str
) -> str | Prefetch:
    if isinstance(item, str):
        return "__".join(
            (
                current_relation
                if isinstance(current_relation, str)
                else current_relation.prefetch_to,
                item,
            )
        )

    current_relation_through = (
        current_relation
        if isinstance(current_relation, str)
        else current_relation.prefetch_through
    )
    current_relation_to = (
        current_relation
        if isinstance(current_relation, str)
        else current_relation.prefetch_to
    )

    new_prefetch = copy.deepcopy(item)

    new_prefetch.prefetch_through = "__".join(
        [current_relation_through, item.prefetch_through]
    )
    new_prefetch.prefetch_to = "__".join([current_relation_to, item.prefetch_to])

    return new_prefetch


def build_computed_related(
    related_attr: list[str | Prefetch] | list[str], current_relation: str | Prefetch
) -> list[str | Prefetch]:
    return [join_prefetch(current_relation, item) for item in related_attr]


def get_custom_related(
    related_attr: list[str | Prefetch] | list[str],
    current_relation: str | Prefetch | None = None,
) -> list[str | Prefetch] | list[str]:
    if current_relation:
        computed_related: list[str | Prefetch] | list[str] = build_computed_related(
            related_attr, current_relation
        )
    else:
        computed_related = related_attr

    return computed_related


def get_model_from_serializer(serializer: SerializerWithMethods[T]) -> Model | None:
    with suppress(AttributeError):
        return serializer.Meta.model  # type: ignore

    with suppress(AttributeError):
        return serializer.child.Meta.model  # type: ignore

    return None
