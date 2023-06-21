from django.test import TestCase

from rest_framework import serializers

from serializer_prefetch import PrefetchingSerializerMixin

from tests.models import Pizza, Topping, Country
from tests.serializers import PizzaSerializer, ToppingSerializer, CountrySerializer


class SerializersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.canada = Country.objects.create(label="Canada")
        cls.usa = Country.objects.create(label="USA")
        cls.china = Country.objects.create(label="China")
        cls.argentina = Country.objects.create(label="Argentina")

        cls.hawaian_pizza = Pizza.objects.create(
            label="Hawaiian", provenance=cls.canada
        )
        cls.ham_topping = Topping.objects.create(
            pizza=cls.hawaian_pizza, label="Ham", origin=cls.china
        )
        cls.pineapple_topping = Topping.objects.create(
            pizza=cls.hawaian_pizza, label="Pineapple", origin=cls.argentina
        )

        cls.pepperoni_pizza = Pizza.objects.create(
            label="Pepperoni", provenance=cls.usa
        )
        cls.pepperoni_topping = Topping.objects.create(
            pizza=cls.pepperoni_pizza, label="Pepperoni", origin=cls.usa
        )

    def test_default_behaviour(self):
        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [{"label": "Ham"}, {"label": "Pineapple"}],
                    "provenance": {"label": "Canada"},
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni"}],
                    "provenance": {"label": "USA"},
                },
            ],
        )

    def test_related_fields(self):
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            toppings = serializers.SerializerMethodField()

            def get_toppings(self, obj):
                return [topping.label for topping in obj.toppings.all()]

            provenance = serializers.SerializerMethodField()

            def get_provenance(self, obj):
                return obj.provenance.label

            class Meta:
                model = Pizza
                fields = ("label", "toppings", "provenance")

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": ["Ham", "Pineapple"],
                    "provenance": "Canada",
                },
                {
                    "label": "Pepperoni",
                    "toppings": ["Pepperoni"],
                    "provenance": "USA",
                },
            ],
        )

        PizzaSerializer.select_related = ("provenance",)
        PizzaSerializer.prefetch_related = ("toppings",)

        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": ["Ham", "Pineapple"],
                    "provenance": "Canada",
                },
                {
                    "label": "Pepperoni",
                    "toppings": ["Pepperoni"],
                    "provenance": "USA",
                },
            ],
        )

        class PizzaSerializer(PizzaSerializer):
            def get_select_related(self):
                return ("provenance",)

            def get_prefetch_related(self):
                return ("toppings",)

        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": ["Ham", "Pineapple"],
                    "provenance": "Canada",
                },
                {
                    "label": "Pepperoni",
                    "toppings": ["Pepperoni"],
                    "provenance": "USA",
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

        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [{"label": "Ham"}, {"label": "Pineapple"}],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni"}],
                },
            ],
        )

        class PizzaSerializer(PizzaSerializer):
            additional_serializers = (
                {
                    "relation_and_field": "toppings",
                    "serializer": ToppingSerializer(),
                },
            )

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [{"label": "Ham"}, {"label": "Pineapple"}],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni"}],
                },
            ],
        )

        class PizzaSerializer(PizzaSerializer):
            def get_additional_serializers(self):
                return (
                    {
                        "relation_and_field": "toppings",
                        "serializer": ToppingSerializer(),
                    },
                )

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [{"label": "Ham"}, {"label": "Pineapple"}],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni"}],
                },
            ],
        )

    def test_default_behaviour_with_depth(self):
        class ToppingSerializer(
            PrefetchingSerializerMixin, serializers.ModelSerializer
        ):
            origin = CountrySerializer()

            class Meta:
                model = Topping
                fields = ("label", "origin")

        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            toppings = ToppingSerializer(many=True)
            provenance = CountrySerializer()

            class Meta:
                model = Pizza
                fields = ("label", "toppings", "provenance")

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [
                        {"label": "Ham", "origin": {"label": "China"}},
                        {"label": "Pineapple", "origin": {"label": "Argentina"}},
                    ],
                    "provenance": {"label": "Canada"},
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni", "origin": {"label": "USA"}}],
                    "provenance": {"label": "USA"},
                },
            ],
        )

    def test_get_additional_serializers_with_depth(self):
        class ToppingSerializer(
            PrefetchingSerializerMixin, serializers.ModelSerializer
        ):
            origin = CountrySerializer()

            class Meta:
                model = Topping
                fields = ("label", "origin")

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

        with self.assertNumQueries(6):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [
                        {"label": "Ham", "origin": {"label": "China"}},
                        {"label": "Pineapple", "origin": {"label": "Argentina"}},
                    ],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni", "origin": {"label": "USA"}}],
                },
            ],
        )

        class PizzaSerializer(PizzaSerializer):
            additional_serializers = (
                {
                    "relation_and_field": "toppings",
                    "serializer": ToppingSerializer(),
                },
            )

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [
                        {"label": "Ham", "origin": {"label": "China"}},
                        {"label": "Pineapple", "origin": {"label": "Argentina"}},
                    ],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni", "origin": {"label": "USA"}}],
                },
            ],
        )

        class PizzaSerializer(PizzaSerializer):
            def get_additional_serializers(self):
                return (
                    {
                        "relation_and_field": "toppings",
                        "serializer": ToppingSerializer(),
                    },
                )

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [
                        {"label": "Ham", "origin": {"label": "China"}},
                        {"label": "Pineapple", "origin": {"label": "Argentina"}},
                    ],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [{"label": "Pepperoni", "origin": {"label": "USA"}}],
                },
            ],
        )

    def test_additional_serializers_with_depth_relation_and_field(self):
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            topping_countries = serializers.SerializerMethodField()

            def get_topping_countries(self, obj):
                return [
                    CountrySerializer(topping.origin).data
                    for topping in obj.toppings.all()
                ]

            class Meta:
                model = Pizza
                fields = ("label", "topping_countries")

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(6):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "topping_countries": [
                        {"label": "China"},
                        {"label": "Argentina"},
                    ],
                },
                {
                    "label": "Pepperoni",
                    "topping_countries": [{"label": "USA"}],
                },
            ],
        )

        class PizzaSerializer(PizzaSerializer):
            additional_serializers = (
                {
                    "relation_and_field": "toppings__origin",
                    "serializer": CountrySerializer(),
                },
            )

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "topping_countries": [
                        {"label": "China"},
                        {"label": "Argentina"},
                    ],
                },
                {
                    "label": "Pepperoni",
                    "topping_countries": [{"label": "USA"}],
                },
            ],
        )

    def test_get_additional_serializer_set_on_child_serializer(self):
        class ToppingSerializer(
            PrefetchingSerializerMixin, serializers.ModelSerializer
        ):
            origin = serializers.SerializerMethodField()

            def get_origin(self, obj):
                return obj.origin.label

            class Meta:
                model = Topping
                fields = ("label", "origin")

        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            toppings = ToppingSerializer(many=True)

            class Meta:
                model = Pizza
                fields = ("label", "toppings")

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(5):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [
                        {"label": "Ham", "origin": "China"},
                        {"label": "Pineapple", "origin": "Argentina"},
                    ],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [
                        {"label": "Pepperoni", "origin": "USA"},
                    ],
                },
            ],
        )

        class ToppingSerializer(ToppingSerializer):
            additional_serializers = (
                {
                    "relation_and_field": "origin",
                    "serializer": CountrySerializer(),
                },
            )

        class PizzaSerializer(PizzaSerializer):
            toppings = ToppingSerializer(many=True)

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [
                        {"label": "Ham", "origin": "China"},
                        {"label": "Pineapple", "origin": "Argentina"},
                    ],
                },
                {
                    "label": "Pepperoni",
                    "toppings": [
                        {"label": "Pepperoni", "origin": "USA"},
                    ],
                },
            ],
        )
