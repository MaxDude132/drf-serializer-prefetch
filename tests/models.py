from django.db import models


class Pizza(models.Model):
    label = models.CharField(max_length=50)


class Topping(models.Model):
    pizza = models.ForeignKey(Pizza, on_delete=models.CASCADE, related_name="toppings")
    label = models.CharField(max_length=50)
