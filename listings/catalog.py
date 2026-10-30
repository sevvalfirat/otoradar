"""
Marka / model kataloğu.

Hem sahte veri üretimi (generate_data) hem de soru çözümleyici (parser)
bu tek kaynağı kullanır; böylece ikisi asla birbirinden kopmaz.
"""

CAR_CATALOG = {
    "Toyota":     {"models": ["Corolla", "Yaris", "C-HR"],   "base_price": 950_000},
    "Volkswagen": {"models": ["Golf", "Passat", "Polo"],     "base_price": 1_100_000},
    "Fiat":       {"models": ["Egea", "Tipo"],               "base_price": 650_000},
    "Renault":    {"models": ["Clio", "Megane", "Talisman"], "base_price": 700_000},
    "Seat":       {"models": ["Ibiza", "Leon"],              "base_price": 800_000},
    "Honda":      {"models": ["Civic", "City"],              "base_price": 1_050_000},
    "Hyundai":    {"models": ["i20", "Tucson"],              "base_price": 900_000},
    "BMW":        {"models": ["3 Serisi", "1 Serisi"],       "base_price": 2_200_000},
    "Mercedes":   {"models": ["C Serisi", "A Serisi"],       "base_price": 2_400_000},
    "Audi":       {"models": ["A3", "A4"],                   "base_price": 2_100_000},
}

# Şehir -> plaka kodu (arayüzdeki plaka rozetleri için)
CITY_PLATES = {
    "Adana": "01",
    "Ankara": "06",
    "Antalya": "07",
    "Bursa": "16",
    "Istanbul": "34",
    "İstanbul": "34",
    "Izmir": "35",
    "İzmir": "35",
}

BRANDS = sorted(CAR_CATALOG)
ALL_MODELS = sorted({m for info in CAR_CATALOG.values() for m in info["models"]})
