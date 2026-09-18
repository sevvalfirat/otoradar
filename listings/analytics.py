import pandas as pd
import numpy as np
from .models import Listing


def get_dataframe(brand=None, model_name=None, fuel_type=None):
    """
    Listing tablosunu Pandas DataFrame'e çevirir.
    İstenirse marka/model/yakıt filtreler.
    """

    qs = Listing.objects.all()

    if brand:
        qs = qs.filter(brand__iexact=brand)

    if model_name:
        qs = qs.filter(model_name__iexact=model_name)

    if fuel_type:
        qs = qs.filter(fuel_type__iexact=fuel_type)

    df = pd.DataFrame.from_records(
        qs.values(
            "brand",
            "model_name",
            "year",
            "mileage_km",
            "price",
            "fuel_type",
            "city"
        )
    )

    if not df.empty:
        df["price"] = df["price"].astype(float)

    return df


def price_stats(brand, model_name=None, year=None):
    """
    Marka/model/yıl bazında fiyat istatistikleri döndürür.
    """

    df = get_dataframe(
        brand=brand,
        model_name=model_name
    )

    if year:
        df = df[df["year"] == year]

    if df.empty:
        return {
            "found": False,
            "message": "Bu kriterlere uygun ilan bulunamadı."
        }

    return {
    "found": True,
    "count": int(len(df)),
    "mean_price": float(round(df["price"].mean(), 2)),
    "median_price": float(round(df["price"].median(), 2)),
    "std_price": float(round(df["price"].std(), 2)) if len(df) > 1 else 0,
    "min_price": float(round(df["price"].min(), 2)),
    "max_price": float(round(df["price"].max(), 2)),
}


def detect_anomaly(listing_id):
    """
    İlan fiyatını aynı marka/model ve benzer yaş grubundaki
    ilanlarla karşılaştırır.

    Z-score değeri 2'den büyük veya -2'den küçükse
    anormal kabul edilir.
    """

    try:
        listing = Listing.objects.get(pk=listing_id)

    except Listing.DoesNotExist:
        return {
            "found": False,
            "message": "İlan bulunamadı."
        }


    df = get_dataframe(
        brand=listing.brand,
        model_name=listing.model_name
    )


    # Benzer yaş grubu (+/- 2 yıl)
    df = df[
        (df["year"] >= listing.year - 2) &
        (df["year"] <= listing.year + 2)
    ]


    if len(df) < 5:
        return {
            "found": True,
            "enough_data": False,
            "message": "Karşılaştırma için yeterli benzer ilan yok."
        }


    mean = df["price"].mean()
    std = df["price"].std()


    if std > 0:
        z_score = (
            float(listing.price) - mean
        ) / std
    else:
        z_score = 0


    is_anomaly = abs(z_score) > 2

    direction = (
        "düşük"
        if z_score < 0
        else "yüksek"
    )


    return {
        "found": True,
        "enough_data": True,

        "listing_price": float(listing.price),

        "group_mean_price": round(mean, 2),

        "z_score": round(float(z_score), 2),

        "is_anomaly": bool(is_anomaly),

        "message": (
            f"Bu ilan, benzer {listing.brand} "
            f"{listing.model_name} "
            f"({listing.year}±2 yıl) ilanların "
            f"ortalamasından belirgin şekilde "
            f"{direction} "
            f"(z-score: {round(float(z_score),2)})."
            if is_anomaly
            else
            "Bu ilan piyasa ortalamasına yakın, normal görünüyor."
        ),
    }