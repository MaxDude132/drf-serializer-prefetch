# Standard libraries
# from unittest import skip

# Django
from django.db.models import Prefetch
from django.test import TestCase

# Rest Framework
from rest_framework import serializers

# drf-serializer-prefetch
from serializer_prefetch import PrefetchingSerializerMixin
from tests.models import Continent, Country, Pizza, Topping
from tests.serializers import (
    # ContinentSerializer,
    CountrySerializer,
    PizzaSerializer,
    ToppingSerializer,
)


class ConditionsTestCase(TestCase):
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

    def test_with_write_only_field(self):
        global PizzaSerializer

        class PizzaSerializer(PizzaSerializer):
            toppings = ToppingSerializer(many=True, write_only=True)

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(1):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "provenance": {"label": "Canada"},
                },
                {
                    "label": "Pepperoni",
                    "provenance": {"label": "USA"},
                },
            ],
        )

    def test_list_is_passed(self):
        pizzas = list(Pizza.objects.all())
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

    def test_dict_is_passed(self):
        pizza = Pizza.objects.first()
        pizza = {
            "label": pizza.label,
            "toppings": [],
            "provenance": {"label": pizza.provenance.label},
        }
        serializer = PizzaSerializer(pizza)

        with self.assertNumQueries(0):
            data = serializer.data

        self.assertEqual(
            data,
            {
                "label": "Hawaiian",
                "toppings": [],
                "provenance": {"label": "Canada"},
            },
        )

    def test_non_model_serializer(self):
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.Serializer):
            toppings = ToppingSerializer(many=True)
            label = serializers.CharField()

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        # Note: the regular Serializer can handle auto prefetching,
        # however it will assume everything to be a prefetch since
        # it cannot check with the field.
        with self.assertNumQueries(2):
            serializer.data

        pizzas = [{"label": "test_label", "toppings": [{"label": "test_topping"}]}]
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(0):
            serializer.data

    def test_prefetch_object_is_passed_with_depth(self):
        class ToppingSerializer(
            PrefetchingSerializerMixin, serializers.ModelSerializer
        ):
            prefetch_related = (
                Prefetch(
                    "origin",
                    queryset=Country.objects.filter(continent__label="Europe"),
                    to_attr="origin_eu",
                ),
            )

            origin_eu = CountrySerializer()

            class Meta:
                model = Topping
                fields = ("label", "origin_eu")

        class PizzaSerializer(
            PrefetchingSerializerMixin, serializers.ModelSerializer
        ):  # noqa: E501
            prefetch_related = (
                Prefetch(
                    "toppings",
                    queryset=Topping.objects.filter(
                        label__in=(
                            "Provolone",
                            "Cheddar",
                            "Parmesan",
                            "Mozzarella",
                            "Paneer",
                        )
                    ),
                    to_attr="cheese_toppings",
                ),
            )

            cheese_toppings = ToppingSerializer(many=True)

            class Meta:
                model = Pizza
                fields = ("label", "cheese_toppings")

        pizza = Pizza.objects.create(
            label="For this test only.",
            provenance=Country.objects.create(label="France"),
        )
        Topping.objects.get_or_create(
            label="Parmesan",
            origin=Country.objects.get_or_create(
                label="Italy",
                continent=Continent.objects.get_or_create(label="Europe")[0],
            )[0],
            pizza=pizza,
        )
        Topping.objects.get_or_create(
            label="Paneer",
            origin=Country.objects.get_or_create(
                label="Some South Asian Country",
                continent=Continent.objects.get_or_create(label="Asia")[0],
            )[0],
            pizza=pizza,
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
                    "cheese_toppings": [],
                },
                {
                    "label": "Pepperoni",
                    "cheese_toppings": [],
                },
                {
                    "label": "For this test only.",
                    "cheese_toppings": [
                        {"label": "Parmesan", "origin_eu": {"label": "Italy"}},
                        {"label": "Paneer", "origin_eu": None},
                    ],
                },
            ],
        )

    # @skip("This test only passes on Django 5.0 and above. Unskip when it's released")
    # def test_prefetch_object_is_passed_with_depth_2(self):
    #     pizza = Pizza.objects.create(
    #         label="For this test only.",
    #         provenance=Country.objects.create(
    #             label="France",
    #             continent=Continent.objects.get_or_create(label="Mistyped Urope")[0],
    #         ),
    #     )
    #     Topping.objects.get_or_create(
    #         label="Parmesan",
    #         origin=Country.objects.get_or_create(
    #             label="Italy",
    #             continent=Continent.objects.get_or_create(label="Europe")[0],
    #         )[0],
    #         pizza=pizza,
    #     )
    #     Topping.objects.get_or_create(
    #         label="Paneer",
    #         origin=Country.objects.get_or_create(
    #             label="Some South Asian Country",
    #             continent=Continent.objects.get_or_create(label="Asia")[0],
    #         )[0],
    #         pizza=pizza,
    #     )
    #     Topping.objects.get_or_create(
    #         label="Other Thing",
    #         origin=Country.objects.get_or_create(
    #             label="Canada",
    #             continent=Continent.objects.get_or_create(label="America")[0],
    #         )[0],
    #         pizza=pizza,
    #     )

    #     class CountrySerializer(
    #         PrefetchingSerializerMixin, serializers.ModelSerializer
    #     ):
    #         prefetch_related = (
    #             Prefetch(
    #                 "continent",
    #                 queryset=Continent.objects.filter(
    #                     label__in=("Europe", "America")
    #                 ),  # noqa: E501
    #                 to_attr="continent_eu",
    #             ),
    #         )

    #         continent = ContinentSerializer(source="continent_eu")

    #         class Meta:
    #             model = Country
    #             fields = ("label", "continent")

    #     class ToppingSerializer(
    #         PrefetchingSerializerMixin, serializers.ModelSerializer
    #     ):
    #         prefetch_related = (
    #             Prefetch(
    #                 "origin",
    #                 queryset=Country.objects.filter(continent__label="Europe"),
    #                 to_attr="origin_eu",
    #             ),
    #         )

    #         origin = CountrySerializer(source="origin_eu")

    #         class Meta:
    #             model = Topping
    #             fields = ("label", "origin")

    #     class PizzaSerializer(
    #         PrefetchingSerializerMixin, serializers.ModelSerializer
    #     ):  # noqa: E501
    #         prefetch_related = ("toppings__origin",)

    #         toppings = ToppingSerializer(many=True)

    #         provenance = CountrySerializer()

    #         class Meta:
    #             model = Pizza
    #             fields = ("label", "toppings", "provenance")

    #     pizzas = Pizza.objects.filter(id=pizza.pk)
    #     serializer = PizzaSerializer(pizzas, many=True)

    #     with self.assertNumQueries(6):
    #         data = serializer.data

    #     self.assertEqual(
    #         data,
    #         [
    #             {
    #                 "label": "For this test only.",
    #                 "toppings": [
    #                     {
    #                         "label": "Parmesan",
    #                         "origin": {
    #                             "label": "Italy",
    #                             "continent": {"label": "Europe"},
    #                         },
    #                     },
    #                     {"label": "Paneer", "origin": None},
    #                     {"label": "Other Thing", "origin": None},
    #                 ],
    #                 "provenance": {"label": "France", "continent": None},
    #             },
    #         ],
    #     )

    def test_with_pagination(self):
        # Pagination returns a list instead of a Queryset
        # Let's test that the prefetching works well still

        pizzas = list(Pizza.objects.all())
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
            serializer.data

    def test_property_properly_handled(self):
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            provenance = CountrySerializer(source="provenance_")

            class Meta:
                model = Pizza
                fields = ("label", "provenance")

        pizzas = list(Pizza.objects.all())
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
            serializer.data

        # If we pass the prefetch_source key, we can tell it where the property
        # fetches the data from
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            provenance = CountrySerializer(
                source="provenance_", prefetch_source="provenance"
            )

            class Meta:
                model = Pizza
                fields = ("label", "provenance")

        pizzas = list(Pizza.objects.all())
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(1):
            serializer.data

        # Passing a wrong prefetch_source should raise a ValueError
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            provenance = CountrySerializer(
                source="provenance_", prefetch_source="wrong_source"
            )

            class Meta:
                model = Pizza
                fields = ("label", "provenance")

        pizzas = list(Pizza.objects.all())
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertRaises(ValueError):
            serializer.data
