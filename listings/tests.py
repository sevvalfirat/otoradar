from django.test import TestCase
from django.urls import reverse

from .agent import is_simple_price_query, local_price_answer
from .analytics import brand_summary_sql, detect_anomaly, price_stats
from .models import Listing
from .parser import parse_vehicle_query


def make(brand="Toyota", model="Corolla", year=2020, price=900_000, **kw):
    return Listing.objects.create(
        brand=brand, model_name=model, year=year, mileage_km=50_000, price=price,
        fuel_type="benzin", transmission="manuel", city="Istanbul", **kw,
    )


class ParserTests(TestCase):
    def test_brand_model_year(self):
        r = parse_vehicle_query("2020 model BMW 3 Serisi kaç TL?")
        self.assertEqual(r, {"brand": "BMW", "model_name": "3 Serisi", "year": 2020})

    def test_model_without_brand(self):
        r = parse_vehicle_query("Egea ne kadar?")
        self.assertEqual((r["brand"], r["model_name"]), ("Fiat", "Egea"))


class RouterTests(TestCase):
    def test_price_question_is_simple(self):
        self.assertTrue(is_simple_price_query("Corolla kaç TL?"))

    def test_opinion_question_goes_to_llm(self):
        self.assertFalse(is_simple_price_query("Toyota Corolla alınır mı?"))

    def test_local_answer_uses_db(self):
        make(price=1_000_000)
        make(price=800_000)
        answer = local_price_answer("2020 Toyota Corolla kaç TL?")
        self.assertIn("900.000 TL", answer)


class AnalyticsTests(TestCase):
    def test_unknown_brand_does_not_crash(self):
        # Eskiden boş DataFrame'de KeyError: 'year' veriyordu
        self.assertFalse(price_stats("Tesla", year=2020)["found"])

    def test_anomaly_detected(self):
        for p in [900_000, 910_000, 890_000, 905_000, 895_000, 900_000]:
            make(price=p)
        cheap = make(price=400_000)
        self.assertTrue(detect_anomaly(cheap.pk)["is_anomaly"])

    def test_brand_summary_sql(self):
        make()
        make(brand="Fiat", model="Egea", price=500_000)
        brands = {r["brand"] for r in brand_summary_sql()}
        self.assertEqual(brands, {"Toyota", "Fiat"})


class PageTests(TestCase):
    def setUp(self):
        self.listing = make()

    def test_pages_load(self):
        for name in ["listing-list", "listing-create", "listing-stats", "agent-chat"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get(reverse("listing-detail", args=[self.listing.pk])).status_code, 200)

    def test_filter_kept_in_pagination(self):
        for _ in range(15):
            make(brand="BMW", model="3 Serisi")
        r = self.client.get(reverse("listing-list"), {"brand": "BMW"})
        self.assertContains(r, "brand=BMW&page=2")

    def test_api_paginated_and_filtered(self):
        make(brand="Fiat", model="Egea")
        data = self.client.get("/api/listings/?brand=Toyota").json()
        self.assertIn("results", data)
        self.assertTrue(all(x["brand"] == "Toyota" for x in data["results"]))
