from rest_framework import serializers

from serializer_prefetch import PrefetchingSerializerMixin

from tests.models import Pizza, Topping, Country


class ToppingSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Topping
        fields = ("label",)


class CountrySerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ("label",)


class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
    toppings = ToppingSerializer(many=True)
    provenance = CountrySerializer()

    class Meta:
        model = Pizza
        fields = ("label", "toppings", "provenance")
