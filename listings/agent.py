"""
OtoRadar AI asistanı.

Akış (hibrit router):
1) Soru basit bir fiyat sorusuysa ("2020 BMW 3 Serisi kaç TL?") cevap,
   LLM'e hiç gitmeden veritabanından üretilir: hızlı, ücretsiz, deterministik.
2) Yorum, anomali veya karmaşık sorular Gemini'ye gider. Gemini, aşağıdaki
   Python fonksiyonlarını "tool" olarak çağırıp gerçek veriyle cevap verir.
3) Gemini'ye ulaşılamazsa kullanıcıya nazik bir mesaj gösterilir,
   gerçek hata terminale loglanır.
"""

import logging
import os

from django.conf import settings

from .analytics import detect_anomaly, price_stats
from .parser import parse_vehicle_query

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = (
    "Şu anda AI asistanına ulaşılamıyor. Fiyat sorularını yine de cevaplayabilirim; "
    "örneğin “2020 Toyota Corolla kaç TL?” diye sorabilirsin."
)

SYSTEM_PROMPT = (
    "Sen OtoRadar adlı araç ilanı platformunun asistanısın. "
    "Kullanıcıların araç fiyatları, piyasa durumu ve ilanlar hakkındaki sorularını "
    "elindeki tool'ları kullanarak gerçek verilerle cevaplıyorsun. "
    "Belirli bir araç için 'alınır mı', 'mantıklı mı', 'pahalı mı' gibi sorularda "
    "get_price_stats ile piyasa verisine bak. "
    "Bir ilan numarası (ID) verilip fiyatının normal olup olmadığı sorulursa "
    "check_listing_anomaly kullan. "
    "Fiyat veya piyasa verisi konusunda asla veri uydurma; tool sonucu yoksa bunu açıkça söyle. "
    "Fiyatları Türk lirası olarak, binlik ayraçla yaz. "
    "Cevaplarını Türkçe, kısa, net ve anlaşılır ver."
)

OPINION_KEYWORDS = [
    "mantıklı", "mantikli", "alınır", "alinir", "almalı", "almali",
    "önerir", "onerir", "öneri", "oneri", "nasıl araç", "nasil arac",
    "iyi mi", "kötü mü", "kotu mu", "avantaj", "dezavantaj", "yorum",
    "tercih", "normal mi", "anormal", "pahalı mı", "pahali mi",
    "ucuz mu",
]

PRICE_KEYWORDS = [
    "fiyat", "ortalama", "medyan", "kaç tl", "kac tl", "kaç lira", "kac lira",
    "ne kadar", "kaça", "kaca", "değerinde", "degerinde", "en ucuz",
    "en pahalı", "en pahali",
]


# --- Gemini'nin kullanacağı tool'lar ---------------------------------------
# Docstring ve type hint'ler, Gemini'ye gönderilen tool tanımını oluşturur.

def get_price_stats(brand: str, model_name: str = None, year: int = None) -> dict:
    """Belirli bir marka/model/yıl için piyasa fiyat istatistiklerini (ilan sayısı, ortalama, medyan, en düşük, en yüksek) döner."""
    return price_stats(brand=brand, model_name=model_name, year=year)


def check_listing_anomaly(listing_id: int) -> dict:
    """Verilen ilan ID'sinin fiyatının, benzer ilanların ortalamasına göre anormal olup olmadığını z-score ile kontrol eder."""
    return detect_anomaly(listing_id)


# --- Hibrit router ----------------------------------------------------------

def is_simple_price_query(message: str) -> bool:
    """Soru yorum istemeyen, açık bir fiyat sorusu mu?"""
    text = message.lower()
    if any(k in text for k in OPINION_KEYWORDS):
        return False
    return any(k in text for k in PRICE_KEYWORDS)


def format_price_stats(vehicle: dict, stats: dict) -> str:
    """İstatistikleri okunabilir Türkçe metne çevirir."""
    title = " ".join(
        p for p in [vehicle["brand"], vehicle["model_name"],
                    f"({vehicle['year']})" if vehicle["year"] else None] if p
    )

    def tl(value):
        return f"{value:,.0f}".replace(",", ".") + " TL"

    return (
        f"**{title}** için piyasa verileri ({stats['count']} ilan üzerinden):\n"
        f"- Ortalama fiyat: {tl(stats['mean_price'])}\n"
        f"- Medyan fiyat: {tl(stats['median_price'])}\n"
        f"- En düşük: {tl(stats['min_price'])}\n"
        f"- En yüksek: {tl(stats['max_price'])}"
    )


def local_price_answer(message: str):
    """Net bir fiyat sorusuysa LLM çağırmadan cevap üretir, değilse None döner."""
    if not is_simple_price_query(message):
        return None
    vehicle = parse_vehicle_query(message)
    if not (vehicle["brand"] and vehicle["model_name"]):
        return None
    stats = price_stats(**vehicle)
    if not stats.get("found"):
        return None
    return format_price_stats(vehicle, stats)


def ask_gemini(message: str) -> str:
    # İçe aktarma ve istemci oluşturma burada: key eksik/bozuksa bile
    # site açılmaya devam eder, sadece bu fonksiyon hata verir.
    from google import genai

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=message,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "tools": [get_price_stats, check_listing_anomaly],
        },
    )
    return response.text or "Bu soruya bir cevap üretemedim, biraz farklı sormayı dener misin?"


def answer_question(message: str) -> dict:
    """Cevabı ve cevabın nereden geldiğini döner: local / gemini / error."""
    local = local_price_answer(message)
    if local:
        logger.info("Lokal cevap: %s", message)
        return {"answer": local, "source": "local"}

    try:
        logger.info("Gemini'ye gönderiliyor: %s", message)
        return {"answer": ask_gemini(message), "source": "gemini"}
    except Exception:
        logger.exception("Gemini API hatası")
        return {"answer": FALLBACK_MESSAGE, "source": "error"}


def ask_agent(user_message: str) -> str:
    """Ödevdeki imza: sadece cevap metnini döner."""
    return answer_question(user_message)["answer"]
