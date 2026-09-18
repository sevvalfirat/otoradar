from django.db import models

class Listing(models.Model):
    FUEL_CHOICES = [
        ("benzin", "Benzin"),
        ("dizel", "Dizel"),
        ("lpg", "LPG"),
        ("elektrik", "Elektrik"),
        ("hibrit", "Hibrit"),
    ]
    TRANSMISSION_CHOICES = [
        ("manuel", "Manuel"),
        ("otomatik", "Otomatik"),
    ]

    brand = models.CharField(max_length=50)          # Marka (Toyota, Fiat...)
    model_name = models.CharField(max_length=50)     # Model (Corolla, Egea...)
    year = models.PositiveIntegerField()
    mileage_km = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES)
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    city = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.brand} {self.model_name} ({self.year})"