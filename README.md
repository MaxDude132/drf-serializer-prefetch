[![codecov](https://codecov.io/gh/MaxDude132/drf-serializer-prefetch/branch/main/graph/badge.svg?token=MFI4E7L7SU)](https://codecov.io/gh/MaxDude132/drf-serializer-prefetch)

# drf-serializer-prefetch

An automatic prefetcher that looks at the serializer fields and determines what needs to be prefetched accordingly.

## Installation

To install, call `pip install drf-serializer-prefetch`.

## Usage

In its most simple form, the serializer prefetch can be used by simply adding `PrefetchingSerializerMixin` to the class definition of the model serializer you want to allow automatic prefetching for like so:

``` python
from rest_framework import serializers
from serializer_prefetch import PrefetchingSerializerMixin


class SomeSerializer(PrefetchingSerializerMixin, serializer.ModelSerializer):
    class Meta:
        model = SomeModel
        fields = (
            'some',
            'fields',
            'are',
            'defined',
        )
```

Using it like this, the Prefetching Serializer will be able to see what fields will be returned and prefetch them accordingly.

However, SerializerMethodFields are an issue for the Prefetching Serializer, as those can make calls that are only done at run time. The Prefetching Serializer does not make any kind of file analysis, and as such cannot know what will happen in those methods. If you are calling a related model in that function, you can define either `select_related` or `prefetch_related` on the model. The fields defined here will also be taken into account. As for usual with Django, you can go as deep as you need here. For example, you could add `user`, or you could add `user__pizza_set`, if you were to loop over the user's pizzas.

For example:

``` python
from rest_framework import serializers
from serializer_prefetch import PrefetchingSerializerMixin


class SomeSerializer(PrefetchingSerializerMixin, serializer.ModelSerializer):
    select_related = ('other_model',)

    other_field = serializers.SerializerMethodField()

    def get_other_field(self, obj):
        return obj.other_model.other_field

    class Meta:
        model = SomeModel
        fields = (
            'some',
            'fields',
            'are',
            'defined',
        )
```

If you need to add some logic to when the prefetching should happen, you can also define `get_select_related` or `get_prefetch_related`:

``` python
from rest_framework import serializers
from serializer_prefetch import PrefetchingSerializerMixin


class SomeSerializer(PrefetchingSerializerMixin, serializer.ModelSerializer):
    def get_select_related(self):
        return ('other_model',)

    other_field = serializers.SerializerMethodField()

    def get_other_field(self, obj):
        return obj.other_model.other_field

    class Meta:
        model = SomeModel
        fields = (
            'some',
            'fields',
            'are',
            'defined',
        )
```

Note that because this is run before the queryset has been split into individual models, we cannot use object logic here. If you need a field for some models only, you can either fetch it for all of them, or fetch it for none of them.

Sometimes, other serializers can be called in a `SerializerMethodField`. For this, you can either define `additional_serializers` like so:

``` python
from rest_framework import serializers
from serializer_prefetch import PrefetchingSerializerMixin


class SomeSerializer(PrefetchingSerializerMixin, serializer.ModelSerializer):
    additional_serializers = (
        {
            'relation_and_field': 'other_model',
            'serializer': OtherModelSerializer(),
        },
    )

    other_field = serializers.SerializerMethodField()

    def get_other_field(self, obj):
        return OtherModelSerializer(obj.other_model, auto_prefetch=False)

    class Meta:
        model = SomeModel
        fields = (
            'some',
            'fields',
            'are',
            'defined',
        )
```

Notice the part `auto_prefetch=False` in the `OtherModelSerializer` call. This is because drf-auto-prefetch uses parents to know if the serializer is at the higher-most level, so that the fetching is only done once. In this case however, the serializer has no parent, but the prefetching is already done by SomeSerializer, so we do not want to do it again. We can tell it to not prefetch by setting `auto_prefetch` to `False`.

As for `select_related` and `prefetch_related`, you can define `get_additional_serializers` instead:

``` python
from rest_framework import serializers
from serializer_prefetch import PrefetchingSerializerMixin


class SomeSerializer(PrefetchingSerializerMixin, serializer.ModelSerializer):
    def get_additional_serializers:
        return (
            {
                'relation_and_field': 'other_model',
                'serializer': OtherModelSerializer(),
            },
        )

    other_field = serializers.SerializerMethodField()

    def get_other_field(self, obj):
        return OtherModelSerializer(obj.other_model, auto_prefetch=False)

    class Meta:
        model = SomeModel
        fields = (
            'some',
            'fields',
            'are',
            'defined',
        )
```

This can be useful to avoid circular dependencies or to add some logic to the prefetching.

----

As of version 1.1.0, the prefetching serializer now allows passing a `Prefetch` object to prefetch_related and to the `relation_and_field` value of `additional_serializers`. This is very useful to avoid fetching more than needed, espescially when filtering is needed in a `SerializerMethodField`. Using this new feature is as simple as using the string lookup:

``` python
from rest_framework import serializers
from serializer_prefetch import PrefetchingSerializerMixin


class SomeSerializer(PrefetchingSerializerMixin, serializer.ModelSerializer):
    prefetch_related = (Prefetch('other_field', queryset=OtherField.objects.filter(some_data='some_value'), to_attr='other_field_filtered'),)

    other_field_filtered = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = SomeModel
        fields = (
            'some',
            'fields',
            'are',
            'defined',
        )
```

This can also be used to filter out the data before sending it to another serializer:

``` python
from rest_framework import serializers
from serializer_prefetch import PrefetchingSerializerMixin


class SomeSerializer(PrefetchingSerializerMixin, serializer.ModelSerializer):
    prefetch_related = (Prefetch('other_field', queryset=OtherField.objects.filter(some_data='some_value'), to_attr='other_field_filtered'),)

    other_field_filtered = OtherFieldSerializer(many=True)

    class Meta:
        model = SomeModel
        fields = (
            'some',
            'fields',
            'are',
            'defined',
        )
```

**IMPORTANT NOTE**: Because of an issue with Django, behaviour could be inconsistant when using to_attr with Prefetch objects. For more information, see: <https://code.djangoproject.com/ticket/34791>

----

As of version 1.1.3, it is now possible to set a new parameter called `force_prefetch` on the serializer. This parameter allows forcing a parameter that would otherwise be in the select_related to be in the prefetch_related. This can be useful when the join time would be longer than just fetching those objects, for instance in the case where there are only 2 or 3 objects to be fetched in total. In certain situations, it is faster to prefetch than to select, so this allows more control over the method used.

----

As of version 1.1.6, you can now pass `prefetch_source` directly to the serializer to tell it to prefetch from another source than the one that is used to get the data. This is especially useful if your source is a property or a callable. By default, the serializer prefetch cannot know what field is actually getting fetched, and will ignore this prefetch entirely as a result. `prefetch_source` allows to let it know which model field should be prefetched.

If the `prefetch_source` passed is not a valid model field, a `ValueError` will be raised.

## Special cases

There are a few situations where you might want to be able to customize the behaviour more. Here are some of the ways you can tweak the Prefetching Serializer to fit the needs of your project.

### Adding logic to the PrefetchingListSerializer

If you had a ListSerializer for you Serializer, you will most likely want to keep its logic. This can be done by simply inheriting from `PrefetchingListSerializer` in that ListSerializer rather than inheriting from `serializers.ListSerializer`. Note that if you do not do this, but add the `PrefetchingSerializerMixin` to the main Serializer, you will get an error saying that the list_serializer_class must inherit from `PrefetchingListSerializer` to be used with the `PrefetchingSerializerMixin`. This is because the behaviour of the prefetching depends on it.

### Adding compatibility with django-zen-queries or other libraries

The goal of this library is to make it easy to not have to think about prefetching. However, this comes with the potential danger of not thinking enough about prefetching. To avoid discovering issues only once in production, you can add django-zen-queries in the mix. To do so, simply extend the `PrefetchingListSerializer` and `PrefetchingSerializerMixin` by defining a new mixin that will be inherited by both. In this mixin, you can override the `queryset_after_prefetch` and `call_to_representation` methods to add some behaviour right after the prefetching has been done on the queryset and right before or after calling `super().to_representation(instance)` on the serializer respectively. For django-zen-queries, it looks something like this:

``` python
from contextlib import nullcontext
from django.conf import settings
import serializer_prefetch
from zen_queries import fetch, queries_disabled


class ZenQueriesPrefetchingMixin:
    def queryset_after_prefetch(self, queryset):
        fetch(queryset)
        return queryset

    def call_to_representation(self, instance):
        with queries_disabled() if settings.DEBUG else nullcontext():
            return super().to_representation(instance)


class PrefetchingListSerializer(
    ZenQueriesPrefetchingMixin, 
    serializer_prefetch.PrefetchingListSerializer
):
    pass


class PrefetchingSerializerMixin(
    ZenQueriesPrefetchingMixin,
    serializer_prefetch.PrefetchingSerializerMixin
):
    default_list_serializer_class = PrefetchingListSerializer
```

The same logic can be applied to other libraries that could need to interact with the queryset between the time it is prefetched and the time it is split into models. Note that `queryset_after_prefetch` is only ever called if the instance passed to the ListSerializer is a Queryset, so you do not need to worry about checking for the type. Similarly, `call_to_representation` is only called if some prefetching was done. If none was done, either because it was not the furthermost parent or because auto_prefetch has been set to `False`, then this method will not be called. If you need a method to always be called, you can define a `to_representation` method in the new `PrefetchingListSerializer` you defined. Do not forget to call the super method!

## Important note

While the Prefetching Serializer does work on regular django-rest-framework serializers, it is really intended to be used with their `ModelSerializer`. If you do use it with a regular Serializer, you will need to define `select_related` and `prefetch_related` for all the fields used. Note that this is still better than having the logic in `get_queryset` in the viewset, as it is kept with its own serializer and will be used properly if the serializer is nested.
