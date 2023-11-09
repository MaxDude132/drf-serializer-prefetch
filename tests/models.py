# Django
from django.db import models


class Continent(models.Model):
    label = models.CharField(max_length=50)


class Country(models.Model):
    label = models.CharField(max_length=50)
    continent = models.ForeignKey(Continent, on_delete=models.CASCADE, null=True)


class Pizza(models.Model):
    label = models.CharField(max_length=50)
    provenance = models.ForeignKey(Country, on_delete=models.CASCADE)

    def get_provenance(self):
        return self.provenance

    def set_provenance(self, value):
        self.provenance = value

    provenance_ = property(get_provenance, set_provenance)

    extra_data = models.JSONField(null=True)


class Topping(models.Model):
    pizza = models.ForeignKey(Pizza, on_delete=models.CASCADE, related_name="toppings")
    label = models.CharField(max_length=50)
    origin = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="toppings"
    )
