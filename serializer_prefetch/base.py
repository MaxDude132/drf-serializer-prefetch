# Standard libraries
from collections.abc import Iterable

# Django
from django.db.models import Model, Prefetch, QuerySet, prefetch_related_objects
from django.utils.translation import gettext as _

# Rest Framework
from rest_framework import serializers
from rest_framework.fields import empty

from serializer_prefetch.utils import (
    get_custom_related,
    get_model_from_serializer,
    is_model_field,
    join_prefetch,
)


class PrefetchingLogicMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._other_prefetching_methods = []

    def get_select_related_data(self, serializer):
        if hasattr(serializer, "get_select_related"):
            return serializer.get_select_related()

        return getattr(serializer, "select_related", [])

    def get_prefetch_related_data(self, serializer):
        if hasattr(serializer, "get_prefetch_related"):
            return serializer.get_prefetch_related()

        return getattr(serializer, "prefetch_related", [])

    def get_additional_serializers_data(self, serializer):
        if hasattr(serializer, "get_additional_serializers"):
            return serializer.get_additional_serializers()

        return getattr(serializer, "additional_serializers", [])

    def get_force_prefetch_data(self, serializer):
        if hasattr(serializer, "get_force_prefetch"):
            return serializer.get_force_prefetch()

        return getattr(serializer, "force_prefetch", [])

    def other_prefetching(self):
        """
        Override this method to add additional prefetching that
        is not done on the queryset itself.

        For example, to do some prefetching on the request.user.
        """

    def queryset_after_prefetch(self, queryset):
        """
        Override this method to make changes to the queryset
        BEFORE it becomes individual models.

        Note: This method is only called when the instance
        is a queryset. If you want to run code in all cases,
        use `wrap_to_representation`.

        This was designed initially for use with django-zen-queries,
        to call fetch on the queryset and be able to use queries_disabled
        """
        return queryset

    def call_to_representation(self, instance):
        """
        Override this method to make changes to the instance
        right before calling the ListSerializer's to_representation
        method, or to wrap it into a context manager.

        This was designed initially for use with django-zen-queries,
        to wrap to_representation in their queries_disabled context
        manager.
        """
        return super().to_representation(instance)

    def call_other_prefetching_methods(self):
        for method in self._other_prefetching_methods:
            method()

    def get_prefetch(
        self,
        serializer: serializers.Serializer,
        current_relation: Prefetch = None,
        should_prefetch: bool = False,
    ):
        if hasattr(serializer, "child"):
            serializer = serializer.child

        force_prefetch = self.get_force_prefetch_data(serializer)
        select_items, prefetch_items = self._get_custom_relations(
            serializer, current_relation, force_prefetch=force_prefetch
        )
        self._extend_relation_items(
            select_items,
            prefetch_items,
            self._get_additional_serializers_relations(serializer, current_relation),
        )
        self._extend_relation_items(
            select_items,
            prefetch_items,
            self._get_serializer_field_relations(
                serializer, current_relation, should_prefetch
            ),
        )
        if hasattr(serializer, "other_prefetching"):
            self._other_prefetching_methods.append(serializer.other_prefetching)

        if should_prefetch:
            return [], select_items + prefetch_items

        return select_items, prefetch_items

    def _extend_relation_items(
        self,
        select_items: Iterable[str],
        prefetch_items: Iterable[Prefetch],
        return_values: Iterable[Iterable[Prefetch | str]],
    ):
        select_items.extend(return_values[0])

        simple_prefetch_to = [
            item.prefetch_to if isinstance(item, Prefetch) else item
            for item in prefetch_items
        ]
        for value in return_values[1]:
            prefetch_to = value.prefetch_to if isinstance(value, Prefetch) else value
            if prefetch_to in simple_prefetch_to:
                continue

            prefetch_items.append(value)

        return select_items, prefetch_items

    def _get_custom_relations(self, serializer, current_relation, *, force_prefetch=()):
        select_related_attr = []
        temp_select_related_attr = self.get_select_related_data(serializer)
        prefetch_related_attr = self.get_prefetch_related_data(serializer)

        for select in temp_select_related_attr:
            if select in force_prefetch:
                prefetch_related_attr.append(select)
            else:
                select_related_attr.append(select)

        custom_select_related = (
            get_custom_related(select_related_attr, current_relation) or []
        )
        custom_prefetch_related = (
            get_custom_related(prefetch_related_attr, current_relation) or []
        )
        return list(custom_select_related), list(custom_prefetch_related)

    def _get_additional_serializers_relations(self, serializer, current_relation):
        additional_serializers = self.get_additional_serializers_data(serializer)

        select_items = []
        prefetch_items = []

        for additional_serializer_data in additional_serializers:
            custom_current_relation = additional_serializer_data.get(
                "relation_and_field", ""
            )

            if current_relation:
                custom_current_relation = join_prefetch(
                    current_relation, custom_current_relation
                )

            if custom_current_relation:
                prefetch_items.append(custom_current_relation)

            additional_serializer = additional_serializer_data.get("serializer")
            if additional_serializer is None:
                raise ValueError(
                    _(
                        "The additional_serializer value is "
                        "missing the key `serializer`."
                    )
                )

            add_to_select, add_to_prefetch = self.get_prefetch(
                additional_serializer,
                current_relation=custom_current_relation,
                # There is no easy way to make sure if it's a prefetch or a select,
                # so we assume it's a prefetch
                should_prefetch=True,
            )
            select_items.extend(add_to_select)
            prefetch_items.extend(add_to_prefetch)

        return select_items, prefetch_items

    def _get_all_prefetch_with_to_attr(self, serializer):
        yield from (
            p
            for p in self.get_prefetch_related_data(serializer)
            if isinstance(p, Prefetch) and p.prefetch_to != p.prefetch_through
        )
        yield from (
            p["relation_and_field"]
            for p in self.get_additional_serializers_data(serializer)
            if isinstance(p["relation_and_field"], Prefetch)
            and p["relation_and_field"].prefetch_to
            != p["relation_and_field"].prefetch_through
        )

    def _get_fields(self, serializer: serializers.Field):
        for field in serializer.fields.values():
            if field.write_only:
                continue

            if not isinstance(field, serializers.BaseSerializer):
                continue

            yield field

    def _get_serializer_field_relations(
        self,
        serializer: serializers.Field,
        current_relation,
        should_prefetch,
    ):
        select_items = []
        prefetch_items = []

        force_prefetch = self.get_force_prefetch_data(serializer)

        for field in self._get_fields(serializer):
            future_should_prefetch = should_prefetch or isinstance(
                field, serializers.ListSerializer
            )

            source = getattr(field, "_prefetch_source", None) or field.source

            is_prefetch_object = False

            # If the source is in the prefetch with a to_attr, then
            # we cannot select it, it must be prefetched, as select_related
            # does not support Prefetch objects.
            for prefetch in self._get_all_prefetch_with_to_attr(serializer):
                if prefetch.prefetch_to == source:
                    is_prefetch_object = True
                    future_should_prefetch = True
                    break

            model = get_model_from_serializer(serializer)
            if not is_prefetch_object and not is_model_field(model, source):
                if getattr(field, "_prefetch_source", None):
                    raise ValueError(
                        _(
                            'The prefetch_source "{}" is not a valid value for '
                            "field {} on serializer {}."
                        ).format(
                            source,
                            field.source,
                            serializer.__class__.__name__,
                        )
                    )

                continue

            append_to = (
                prefetch_items
                if future_should_prefetch or source in force_prefetch
                else select_items
            )

            if current_relation:
                source = join_prefetch(current_relation, source)

            add_to_select, add_to_prefetch = self.get_prefetch(
                field,
                current_relation=source,
                should_prefetch=future_should_prefetch,
            )

            meta = (
                getattr(field.child, "Meta", None)
                if isinstance(field, serializers.ListSerializer)
                else getattr(field, "Meta", None)
            )
            if meta:
                model = getattr(meta, "model", None)
            if meta and model:
                append_to.append(source)
                select_items.extend(add_to_select)
                prefetch_items.extend(add_to_prefetch)

        return select_items, prefetch_items


class List(list):
    _serializer_prefetch_done = False


class PrefetchingListSerializer(PrefetchingLogicMixin, serializers.ListSerializer):
    def __init__(
        self, *args, auto_prefetch=True, prefetch_source: str | None = None, **kwargs
    ):
        self._auto_prefetch = auto_prefetch
        self._prefetch_source = prefetch_source
        super().__init__(*args, **kwargs)

    def to_representation(self, instance, *args, **kwargs):
        prefetch_done = getattr(instance, "_serializer_prefetch_done", False)
        if prefetch_done or self.parent is not None or not self._auto_prefetch:
            return super().to_representation(instance)

        child = self.child
        select_items, prefetch_items = self.get_prefetch(child)

        if isinstance(instance, QuerySet):
            if select_items:
                instance = instance.select_related(*select_items)
            instance = instance.prefetch_related(*prefetch_items)
            instance = self.queryset_after_prefetch(instance)

        else:
            if not isinstance(instance, Iterable):
                raise ValueError(
                    _(
                        "instance is not an Iterable. Do not pass "
                        "`many=True` to the serializer."
                    )
                )

            for related_lookup in select_items + prefetch_items:
                prefetch_related_objects(instance, related_lookup)

        if isinstance(instance, list):
            instance = List(instance)

        instance._serializer_prefetch_done = True

        self.call_other_prefetching_methods()

        return self.call_to_representation(instance)


class Dict(dict):
    _serializer_prefetch_done = False


class PrefetchingSerializerMixin(PrefetchingLogicMixin):
    default_list_serializer_class = PrefetchingListSerializer

    def to_representation(self, instance, *args, **kwargs):
        prefetch_done = getattr(instance, "_serializer_prefetch_done", False)
        if (
            not prefetch_done
            and self._auto_prefetch
            and not self.parent
            and not getattr(instance, "_prefetched_objects_cache", None)
        ):
            select_items, prefetch_items = self.get_prefetch(self)

            for related_lookup in select_items + prefetch_items:
                try:
                    prefetch_related_objects([instance], related_lookup)
                except AttributeError as exc:
                    raise ValueError(
                        _(
                            "Got an AttributeError. You might have forgotten to "
                            "add `many=True` on the serializer."
                        )
                    ) from exc

            if isinstance(instance, dict):
                instance = Dict(instance)
            instance._serializer_prefetch_done = True

            self.call_other_prefetching_methods()

            if isinstance(instance, Model):
                return self.call_to_representation(instance)

        return super().to_representation(instance)

    def __init__(
        self,
        instance=None,
        data=empty,
        auto_prefetch: bool = True,
        prefetch_source: str | None = None,
        **kwargs
    ):
        self._auto_prefetch = auto_prefetch
        self._prefetch_source = prefetch_source
        super().__init__(instance, data, **kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        allow_empty = kwargs.pop("allow_empty", None)
        max_length = kwargs.pop("max_length", None)
        min_length = kwargs.pop("min_length", None)
        auto_prefetch = kwargs.pop("auto_prefetch", True)
        child_serializer = cls(*args, **kwargs)
        list_kwargs = {
            "child": child_serializer,
            "auto_prefetch": auto_prefetch,
        }
        if allow_empty is not None:
            list_kwargs["allow_empty"] = allow_empty
        if max_length is not None:
            list_kwargs["max_length"] = max_length
        if min_length is not None:
            list_kwargs["min_length"] = min_length
        list_kwargs.update(
            {
                key: value
                for key, value in kwargs.items()
                if key in serializers.LIST_SERIALIZER_KWARGS
            }
        )

        meta = getattr(cls, "Meta", None)
        list_serializer = getattr(
            meta, "list_serializer_class", cls.default_list_serializer_class
        )
        if not issubclass(list_serializer, cls.default_list_serializer_class):
            raise ValueError(
                _(
                    "list_serializer_class must inherit from PrefetchingListSerializer"
                    " to use with the PrefetchingSerializerMixin."
                )
            )

        return list_serializer(*args, **list_kwargs)
