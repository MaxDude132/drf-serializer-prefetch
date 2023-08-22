from django.db.models import Prefetch
from django.test import TestCase

from rest_framework import serializers

from serializer_prefetch import PrefetchingSerializerMixin

from tests.models import Continent, Pizza, Topping, Country
from tests.serializers import PizzaSerializer, ToppingSerializer, CountrySerializer


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

        # Note: the regular Serializer cannot handle auto prefetching,
        # it has to be done manually
        with self.assertNumQueries(3):
            serializer.data

        class PizzaSerializer(PizzaSerializer):
            additional_serializers = (
                {"relation_and_field": "toppings", "serializer": ToppingSerializer()},
            )

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
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

        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
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

    def test_with_pagination(self):
        # Pagination returns a list instead of a Queryset
        # Let's test that the prefetching works well still

        pizzas = list(Pizza.objects.all())
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
            serializer.data
