import re

from .catalog import CAR_CATALOG


def _normalize(text: str) -> str:
    """Türkçe karakterleri sadeleştirip küçük harfe çevirir (İ/ı sorunlarını önler)."""
    table = str.maketrans("İIıŞşĞğÜüÖöÇç", "iiissgguuoocc")
    return text.translate(table).lower()


def parse_vehicle_query(message: str) -> dict:
    """
    Kullanıcı mesajından marka, model ve yılı çıkarır.

    - Yıl: 19xx / 20xx biçimindeki ilk sayı
    - Marka: katalogdaki marka adı geçiyorsa
    - Model: markanın modellerinden biri geçiyorsa; marka yazılmadan
      sadece model yazıldıysa ("Corolla kaç TL?") marka modelden bulunur.
    """
    text = _normalize(message)
    result = {"brand": None, "model_name": None, "year": None}

    year_match = re.search(r"\b(19|20)\d{2}\b", message)
    if year_match:
        result["year"] = int(year_match.group())

    for brand, info in CAR_CATALOG.items():
        if _normalize(brand) in text:
            result["brand"] = brand
            for model in info["models"]:
                if _normalize(model) in text:
                    result["model_name"] = model
                    break
            return result

    # Marka yazılmamış: modelden markayı bul
    for brand, info in CAR_CATALOG.items():
        for model in info["models"]:
            if re.search(rf"\b{re.escape(_normalize(model))}\b", text):
                result["brand"] = brand
                result["model_name"] = model
                return result

    return result
