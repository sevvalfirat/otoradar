import random
from datetime import date

from django.core.management.base import BaseCommand

from listings.catalog import CAR_CATALOG
from listings.models import Listing

CITIES = ["Istanbul", "Ankara", "Izmir", "Bursa", "Antalya", "Adana"]
FUEL = ["benzin", "dizel", "lpg", "hibrit"]
TRANS = ["manuel", "otomatik"]

NORMAL_DESCRIPTIONS = [
    "Bakımları yetkili serviste yapıldı.",
    "Değişensiz, boyasız.",
    "İlk sahibinden, garajda tutuldu.",
    "Lastikler yeni, muayenesi yeni yapıldı.",
    "Ufak çizikler dışında temiz.",
    "",
]


class Command(BaseCommand):
    help = "Sentetik araç ilanı verisi üretir"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=3000, help="Üretilecek ilan sayısı")
        parser.add_argument("--anomaly-rate", type=float, default=0.03,
                            help="Bilinçli olarak çok ucuz/pahalı üretilecek ilan oranı")
        parser.add_argument("--clear", action="store_true",
                            help="Önce mevcut bütün ilanları siler")

    def handle(self, *args, **options):
        count = options["count"]
        anomaly_rate = options["anomaly_rate"]
        this_year = date.today().year

        if options["clear"]:
            deleted, _ = Listing.objects.all().delete()
            self.stdout.write(f"{deleted} eski ilan silindi.")

        objs, anomalies = [], 0
        for _ in range(count):
            brand = random.choice(list(CAR_CATALOG))
            info = CAR_CATALOG[brand]
            year = random.randint(2012, this_year)
            age = this_year - year

            # Yaş arttıkça kilometre artar, fiyat her yıl ~%7 düşer
            mileage = max(0, int(random.gauss(age * 18000, 8000)))
            price = info["base_price"] * (0.93 ** age) * random.uniform(0.9, 1.1)

            # Belirli oranda bilinçli anomali (anomali tespiti bunları yakalamalı)
            is_anomaly = random.random() < anomaly_rate
            description = random.choice(NORMAL_DESCRIPTIONS)
            if is_anomaly:
                factor = random.choice([0.5, 0.55, 1.6, 1.7])
                price *= factor
                anomalies += 1
                description = ("Acil satılık, fiyat düşüktür." if factor < 1
                               else "Full paket, fiyatta pazarlık yoktur.")

            objs.append(Listing(
                brand=brand,
                model_name=random.choice(info["models"]),
                year=year,
                mileage_km=mileage,
                price=round(price, 2),
                fuel_type=random.choice(FUEL),
                transmission=random.choice(TRANS),
                city=random.choice(CITIES),
                description=description,
            ))

        Listing.objects.bulk_create(objs, batch_size=500)
        self.stdout.write(self.style.SUCCESS(
            f"{count} ilan oluşturuldu ({anomalies} bilinçli anomali dahil)."
        ))
