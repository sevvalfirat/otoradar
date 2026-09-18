import random
from django.core.management.base import BaseCommand
from faker import Faker
from listings.models import Listing

fake = Faker("tr_TR")

# Marka -> model -> baz fiyat aralığı (gerçekçi dağılım için)
CAR_CATALOG = {
    "Toyota":    {"models": ["Corolla", "Yaris", "C-HR"],        "base_price": 950_000},
    "Volkswagen":{"models": ["Golf", "Passat", "Polo"],          "base_price": 1_100_000},
    "Fiat":      {"models": ["Egea", "Tipo"],                    "base_price": 650_000},
    "Renault":   {"models": ["Clio", "Megane", "Talisman"],      "base_price": 700_000},
    "Seat":      {"models": ["Ibiza", "Leon"],                   "base_price": 800_000},
    "Honda":     {"models": ["Civic", "City"],                   "base_price": 1_050_000},
    "Hyundai":   {"models": ["i20", "Tucson"],                   "base_price": 900_000},
    "BMW":       {"models": ["3 Serisi", "1 Serisi"],            "base_price": 2_200_000},
    "Mercedes":  {"models": ["C Serisi", "A Serisi"],            "base_price": 2_400_000},
    "Audi":      {"models": ["A3", "A4"],                        "base_price": 2_100_000},
}

CITIES = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana"]
FUEL = ["benzin", "dizel", "lpg", "hibrit"]
TRANS = ["manuel", "otomatik"]


class Command(BaseCommand):
    help = "Sentetik araç ilanı verisi üretir"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=3000)
        parser.add_argument("--anomaly-rate", type=float, default=0.03,
                             help="Anormal (çok ucuz/pahalı) ilan oranı")

    def handle(self, *args, **options):
        count = options["count"]
        anomaly_rate = options["anomaly_rate"]
        objs = []

        for _ in range(count):
            brand = random.choice(list(CAR_CATALOG.keys()))
            info = CAR_CATALOG[brand]
            model_name = random.choice(info["models"])
            year = random.randint(2012, 2024)
            age = 2026 - year

            # Yaş ve kilometre arttıkça fiyat düşer, gerçekçi bir formül
            mileage = max(0, int(random.gauss(age * 18000, 8000)))
            price = info["base_price"] * (0.93 ** age) * random.uniform(0.9, 1.1)

            # %3 ihtimalle bilinçli anomali üret (agent bunları yakalayacak)
            is_anomaly = random.random() < anomaly_rate
            if is_anomaly:
                price *= random.choice([0.5, 0.55, 1.6, 1.7])  # çok ucuz ya da çok pahalı

            objs.append(Listing(
                brand=brand,
                model_name=model_name,
                year=year,
                mileage_km=mileage,
                price=round(price, 2),
                fuel_type=random.choice(FUEL),
                transmission=random.choice(TRANS),
                city=random.choice(CITIES),
                description="" if not is_anomaly else "Acil satılık, fiyat düşüktür",
            ))

        Listing.objects.bulk_create(objs, batch_size=500)
        self.stdout.write(self.style.SUCCESS(
            f"{count} ilan oluşturuldu ({int(count*anomaly_rate)} adet bilinçli anomali dahil)"
        ))