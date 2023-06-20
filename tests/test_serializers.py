from django.test import TestCase

from rest_framework import serializers

from serializer_prefetch import PrefetchingSerializerMixin

from tests.models import Pizza, Topping


class ToppingSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Topping
        fields = ("label",)


class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
    toppings = ToppingSerializer(many=True)

    class Meta:
        model = Pizza
        fields = ("label", "toppings")


class SerializersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.hawaian_pizza = Pizza.objects.create(label="Hawaïan")
        cls.ham_topping = Topping.objects.create(pizza=cls.hawaian_pizza, label="Ham")
        cls.pineapple_topping = Topping.objects.create(
            pizza=cls.hawaian_pizza, label="Pineapple"
        )

        cls.pepperoni_pizza = Pizza.objects.create(label="Pepperoni")
        cls.ham_topping = Topping.objects.create(
            pizza=cls.pepperoni_pizza, label="Pepperoni"
        )

    def test_default_behaviour(self):
        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        # We expect only 2 queries, one for each table
        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaïan",
                    "toppings": [{"label": "Ham"}, {"label": "Pineapple"}],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni"}],
                },
            ],
        )

    def test_serializer_method_field(self):
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            toppings = serializers.SerializerMethodField()

            def get_toppings(self, obj):
                return [topping.label for topping in obj.toppings.all()]

            class Meta:
                model = Pizza
                fields = ("label", "toppings")

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        # We expect 3 queries, because prefetching is not done properly
        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaïan",
                    "toppings": ["Ham", "Pineapple"],
                },
                {
                    "label": "Pepperoni",
                    "toppings": ["Pepperoni"],
                },
            ],
        )

        PizzaSerializer.prefetch_related = ("toppings",)

        serializer = PizzaSerializer(pizzas, many=True)

        # We expect 2 queries, because we improved prefetching
        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaïan",
                    "toppings": ["Ham", "Pineapple"],
                },
                {
                    "label": "Pepperoni",
                    "toppings": ["Pepperoni"],
                },
            ],
        )

        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            def get_prefetch_related(self):
                return ("toppings",)

            toppings = serializers.SerializerMethodField()

            def get_toppings(self, obj):
                return [topping.label for topping in obj.toppings.all()]

            class Meta:
                model = Pizza
                fields = ("label", "toppings")

        serializer = PizzaSerializer(pizzas, many=True)

        # We expect 2 queries, because we improved prefetching
        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaïan",
                    "toppings": ["Ham", "Pineapple"],
                },
                {
                    "label": "Pepperoni",
                    "toppings": ["Pepperoni"],
                },
            ],
        )

    def test_get_additional_serializers(self):
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            toppings = serializers.SerializerMethodField()

            def get_toppings(self, obj):
                return [
                    ToppingSerializer(topping).data for topping in obj.toppings.all()
                ]

            class Meta:
                model = Pizza
                fields = ("label", "toppings")

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        # We expect 3 queries, because prefetching is not done properly
        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaïan",
                    "toppings": [{"label": "Ham"}, {"label": "Pineapple"}],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni"}],
                },
            ],
        )

        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            additional_serializers = (
                {
                    "relation_and_field": "toppings",
                    "serializers": ToppingSerializer(),
                },
            )

            toppings = serializers.SerializerMethodField()

            def get_toppings(self, obj):
                return [
                    ToppingSerializer(topping).data for topping in obj.toppings.all()
                ]

            class Meta:
                model = Pizza
                fields = ("label", "toppings")

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        # We expect 3 queries, because prefetching is not done properly
        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaïan",
                    "toppings": [{"label": "Ham"}, {"label": "Pineapple"}],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni"}],
                },
            ],
        )
