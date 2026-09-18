import os

from dotenv import load_dotenv

from google import genai

from .analytics import price_stats, detect_anomaly

from .parser import parse_vehicle_query


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# Gemini kullanmadan önce basit fiyat sorularını yakala
def local_price_check(message: str):

    vehicle = parse_vehicle_query(message)

    if vehicle["brand"] and vehicle["model_name"]:

        return price_stats(
            brand=vehicle["brand"],
            model_name=vehicle["model_name"],
            year=vehicle["year"]
        )

    return None



def get_price_stats(
    brand: str,
    model_name: str = None,
    year: int = None
) -> dict:
    """
    Belirli marka/model/yıl için piyasa fiyat istatistiklerini döner.
    """

    return price_stats(
        brand=brand,
        model_name=model_name,
        year=year
    )



def check_listing_anomaly(
    listing_id: int
) -> dict:
    """
    Belirli ilan ID'sinin fiyat anomalisi kontrolünü yapar.
    """

    return detect_anomaly(
        listing_id
    )



SYSTEM_PROMPT = (

    "Sen OtoRadar adlı araç ilanı platformunun asistanısın. "

    "Kullanıcıların araç fiyatları hakkındaki sorularını "
    "elindeki tool'ları kullanarak gerçek verilerle cevaplıyorsun. "

    "Asla veri uydurma. "

    "Cevaplarını Türkçe, kısa ve net ver."

)

def format_price_stats(vehicle: dict, stats: dict) -> str:
    """Ham istatistik dict'ini okunabilir Türkçe metne çevirir."""
    parts = [vehicle["brand"]]
    if vehicle["model_name"]:
        parts.append(vehicle["model_name"])
    if vehicle["year"]:
        parts.append(f"({vehicle['year']})")
    title = " ".join(parts)

    return (
        f"**{title}** için piyasa verileri ({stats['count']} ilan üzerinden):\n\n"
        f"- Ortalama fiyat: {stats['mean_price']:,.0f} TL\n"
        f"- Medyan fiyat: {stats['median_price']:,.0f} TL\n"
        f"- En düşük: {stats['min_price']:,.0f} TL\n"
        f"- En yüksek: {stats['max_price']:,.0f} TL"
    )

def ask_agent(user_message: str) -> str:

    # 1) Önce Gemini kullanmadan lokal analiz yap
    vehicle = parse_vehicle_query(user_message)
    local_result = local_price_check(user_message)

    if local_result and local_result.get("found"):
        return format_price_stats(vehicle, local_result)

    # 2) Daha karmaşık sorular Gemini'ye gider
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=user_message,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "tools": [get_price_stats, check_listing_anomaly],
        },
    )
    return response.text