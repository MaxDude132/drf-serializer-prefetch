# Django
from django.db.models import Prefetch
from django.test import TestCase

# Rest Framework
from rest_framework import serializers

# drf-serializer-prefetch
from serializer_prefetch import PrefetchingSerializerMixin
from tests.models import Continent, Country, Pizza, Topping
from tests.serializers import CountrySerializer, PizzaSerializer, ToppingSerializer


class SerializersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.america = Continent.objects.create(label="America")
        cls.asia = Continent.objects.create(label="Asia")

        cls.canada = Country.objects.create(label="Canada", continent=cls.america)
        cls.usa = Country.objects.create(label="USA", continent=cls.america)
        cls.china = Country.objects.create(label="China", continent=cls.asia)
        cls.argentina = Country.objects.create(label="Argentina", continent=cls.america)

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

        Topping.objects.create(
            pizza=self.pepperoni_pizza, label="Mozzarella", origin=self.canada
        )

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(5):
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
                    "toppings": ["Pepperoni", "Mozzarella"],
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
                    "toppings": ["Pepperoni", "Mozzarella"],
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
                    "toppings": ["Pepperoni", "Mozzarella"],
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

    def test_select_related_with_depth(self):
        class CountrySerializer(
            PrefetchingSerializerMixin, serializers.ModelSerializer
        ):
            continent = serializers.SerializerMethodField()

            def get_continent(self, obj):
                return obj.continent.label

            class Meta:
                model = Country
                fields = ("label", "continent")

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

        with self.assertNumQueries(8):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [
                        {
                            "label": "Ham",
                            "origin": {"label": "China", "continent": "Asia"},
                        },
                        {
                            "label": "Pineapple",
                            "origin": {"label": "Argentina", "continent": "America"},
                        },
                    ],
                    "provenance": {"label": "Canada", "continent": "America"},
                },
                {
                    "label": "Pepperoni",
                    "toppings": [
                        {
                            "label": "Pepperoni",
                            "origin": {"label": "USA", "continent": "America"},
                        }
                    ],
                    "provenance": {"label": "USA", "continent": "America"},
                },
            ],
        )

        class CountrySerializer(
            PrefetchingSerializerMixin, serializers.ModelSerializer
        ):
            select_related = ("continent",)

            continent = serializers.SerializerMethodField()

            def get_continent(self, obj):
                return obj.continent.label

            class Meta:
                model = Country
                fields = ("label", "continent")

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

        with self.assertNumQueries(4):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "toppings": [
                        {
                            "label": "Ham",
                            "origin": {"label": "China", "continent": "Asia"},
                        },
                        {
                            "label": "Pineapple",
                            "origin": {"label": "Argentina", "continent": "America"},
                        },
                    ],
                    "provenance": {"label": "Canada", "continent": "America"},
                },
                {
                    "label": "Pepperoni",
                    "toppings": [
                        {
                            "label": "Pepperoni",
                            "origin": {"label": "USA", "continent": "America"},
                        }
                    ],
                    "provenance": {"label": "USA", "continent": "America"},
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

    def test_allow_passing_prefetch_object(self):
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            american_toppings = serializers.SerializerMethodField()

            def get_american_toppings(self, obj):
                return [
                    topping.label
                    for topping in obj.toppings.filter(
                        origin__continent__label="America"
                    )
                ]

            class Meta:
                model = Pizza
                fields = ("label", "american_toppings")

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(3):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "american_toppings": ["Pineapple"],
                },
                {
                    "label": "Pepperoni",
                    "american_toppings": ["Pepperoni"],
                },
            ],
        )

        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            prefetch_related = (
                Prefetch(
                    "toppings",
                    queryset=Topping.objects.filter(origin__continent__label="America"),
                    to_attr="american_toppings",
                ),
            )

            american_toppings = serializers.SerializerMethodField()

            def get_american_toppings(self, obj):
                return [topping.label for topping in obj.american_toppings]

            class Meta:
                model = Pizza
                fields = ("label", "american_toppings")

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
            data = serializer.data

        self.assertEqual(
            data,
            [
                {
                    "label": "Hawaiian",
                    "american_toppings": ["Pineapple"],
                },
                {
                    "label": "Pepperoni",
                    "american_toppings": ["Pepperoni"],
                },
            ],
        )

    def test_allow_passing_prefetch_object_with_depth(self):
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
                    "toppings": [{"label": "Pepperoni", "origin": "USA"}],
                },
            ],
        )

        class ToppingSerializer(ToppingSerializer):
            prefetch_related = (Prefetch("origin"),)

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
                    "toppings": [{"label": "Pepperoni", "origin": "USA"}],
                },
            ],
        )

    def test_force_prefetch(self):
        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            provenance = CountrySerializer()

            class Meta:
                model = Pizza
                fields = ("label", "provenance")

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

        PizzaSerializer.force_prefetch = ("provenance",)

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
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

        PizzaSerializer.select_related = ("provenance",)

        pizzas = Pizza.objects.all()
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(2):
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

    def test_non_model_serializer_not_prefetched(self):
        class ExtraDataSerializer(serializers.Serializer):
            label = serializers.CharField()

        class PizzaSerializer(PrefetchingSerializerMixin, serializers.ModelSerializer):
            extra_data = ExtraDataSerializer()

            class Meta:
                model = Pizza
                fields = ("label", "extra_data")

        Pizza.objects.create(
            label="Margherita",
            extra_data={"label": "Margherita"},
            provenance=self.canada,
        )
        pizzas = Pizza.objects.filter(label="Margherita")
        serializer = PizzaSerializer(pizzas, many=True)

        with self.assertNumQueries(1):
            data = serializer.data

        self.assertEqual(
            data,
            [{"label": "Margherita", "extra_data": {"label": "Margherita"}}],
        )
