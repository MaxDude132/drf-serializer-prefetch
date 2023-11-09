from contextlib import suppress
import copy

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Prefetch
from django.db.models.fields import Field as DjangoModelField
from django.db.models.fields.related import ForeignObjectRel


def is_model_field(model, source):
    if hasattr(model, "_meta"):
        try:
            model_field = model._meta.get_field(source)
            if not isinstance(model_field, DjangoModelField | ForeignObjectRel):
                return False
        except FieldDoesNotExist:
            return False

    return True


def join_prefetch(current_relation: Prefetch | str, item: Prefetch | str):
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


def build_computed_related(related_attr, current_relation):
    return [join_prefetch(current_relation, item) for item in related_attr]


def get_custom_related(related_attr, current_relation=None):
    if current_relation:
        computed_related = build_computed_related(related_attr, current_relation)
    else:
        computed_related = related_attr

    return computed_related


def get_model_from_serializer(serializer):
    with suppress(AttributeError):
        return serializer.Meta.model

    with suppress(AttributeError):
        return serializer.child.Meta.model
