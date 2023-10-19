# Django
from django.test import TestCase

# Rest Framework
from rest_framework import serializers

# drf-serializer-prefetch
from tests.models import Country, Pizza, Topping
from tests.serializers import PizzaSerializer


class ErrorsTestCase(TestCase):
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

    def test_value_error_if_serializer_not_in_additional_serializer_data(self):
        class LocalPizzaSerializer(PizzaSerializer):
            additional_serializers = ({"relation_and_field": "toppings"},)

        serializer = LocalPizzaSerializer(Pizza.objects.all(), many=True)

        with self.assertRaises(ValueError):
            serializer.data

    def test_list_serializer_does_not_subclass(self):
        class PizzaListSerializer(serializers.ListSerializer):
            pass

        class LocalPizzaSerializer(PizzaSerializer):
            class Meta:
                model = Pizza
                fields = ("label", "toppings", "provenance")
                list_serializer_class = PizzaListSerializer

        pizzas = Pizza.objects.all()
        with self.assertRaises(ValueError):
            LocalPizzaSerializer(pizzas, many=True)

    def test_many_true_wrongly_passed(self):
        pizza = Pizza.objects.first()
        serializer = PizzaSerializer(pizza, many=True)

        with self.assertRaises(ValueError):
            serializer.data

    def test_many_true_not_passed_but_should(self):
        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas)

        with self.assertRaises(ValueError):
            serializer.data
