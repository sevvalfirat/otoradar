"""
Veri analizi fonksiyonları (Pandas + ham SQL).

Bu fonksiyonlar hem web sayfalarında hem de AI asistanının
"tool"ları olarak kullanılır.
"""

import pandas as pd
from django.db import connection

from .models import Listing

COLUMNS = ["id", "brand", "model_name", "year", "mileage_km", "price", "fuel_type", "city"]


def get_dataframe(brand=None, model_name=None, fuel_type=None):
    """Listing tablosunu (isteğe bağlı filtreli) Pandas DataFrame'e çevirir."""
    qs = Listing.objects.all()
    if brand:
        qs = qs.filter(brand__iexact=brand)
    if model_name:
        qs = qs.filter(model_name__iexact=model_name)
    if fuel_type:
        qs = qs.filter(fuel_type__iexact=fuel_type)

    # columns= verilince sonuç boş olsa bile sütunlar var olur (KeyError önlenir)
    df = pd.DataFrame.from_records(qs.values(*COLUMNS), columns=COLUMNS)
    if not df.empty:
        df["price"] = df["price"].astype(float)
    return df


def price_stats(brand, model_name=None, year=None):
    """Marka / model / yıl için fiyat istatistikleri döner."""
    not_found = {"found": False, "message": "Bu kriterlere uygun ilan bulunamadı."}

    df = get_dataframe(brand=brand, model_name=model_name)
    if df.empty:
        return not_found

    if year:
        df = df[df["year"] == int(year)]
        if df.empty:
            return not_found

    return {
        "found": True,
        "count": int(len(df)),
        "mean_price": float(round(df["price"].mean(), 2)),
        "median_price": float(round(df["price"].median(), 2)),
        "std_price": float(round(df["price"].std(), 2)) if len(df) > 1 else 0.0,
        "min_price": float(round(df["price"].min(), 2)),
        "max_price": float(round(df["price"].max(), 2)),
    }


def detect_anomaly(listing_id):
    """
    İlan fiyatını aynı marka + model ve ±2 yıl grubuyla karşılaştırır.
    |z-score| > 2 ise anomali kabul edilir.
    """
    try:
        listing = Listing.objects.get(pk=listing_id)
    except Listing.DoesNotExist:
        return {"found": False, "message": "İlan bulunamadı."}

    df = get_dataframe(brand=listing.brand, model_name=listing.model_name)
    df = df[(df["year"] >= listing.year - 2) & (df["year"] <= listing.year + 2)]

    if len(df) < 5:
        return {
            "found": True,
            "enough_data": False,
            "group_size": int(len(df)),
            "message": "Karşılaştırma için yeterli benzer ilan yok.",
        }

    mean, std = float(df["price"].mean()), float(df["price"].std())
    price = float(listing.price)
    z_score = (price - mean) / std if std > 0 else 0.0
    is_anomaly = abs(z_score) > 2
    direction = "düşük" if z_score < 0 else "yüksek"

    if is_anomaly:
        message = (
            f"Bu ilan, benzer {listing.brand} {listing.model_name} ({listing.year} ±2 yıl) "
            f"ilanların ortalamasından belirgin şekilde {direction} (z-score: {z_score:.2f})."
        )
    else:
        message = "Bu ilan piyasa ortalamasına yakın, normal görünüyor."

    return {
        "found": True,
        "enough_data": True,
        "listing_price": round(price, 2),
        "group_mean_price": round(mean, 2),
        "group_std_price": round(std, 2),
        "group_size": int(len(df)),
        "z_score": round(z_score, 2),
        "is_anomaly": bool(is_anomaly),
        "direction": direction,
        "message": message,
    }


def brand_summary_sql():
    """Ham SQL ile marka bazlı ilan sayısı ve ortalama fiyat (GROUP BY)."""
    sql = """
        SELECT brand, COUNT(*) AS adet, ROUND(AVG(price), 0) AS ort_fiyat
        FROM listings_listing
        GROUP BY brand
        ORDER BY ort_fiyat DESC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    return [{"brand": r[0], "count": r[1], "avg_price": float(r[2] or 0)} for r in rows]


def yearly_price_trend():
    """Pandas ile model yılına göre ortalama fiyat (grafik için)."""
    df = get_dataframe()
    if df.empty:
        return []
    grouped = df.groupby("year")["price"].agg(["count", "mean"]).reset_index()
    return [
        {"year": int(r.year), "count": int(r["count"]), "avg_price": round(float(r["mean"]), 0)}
        for _, r in grouped.iterrows()
    ]
