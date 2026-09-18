import re


CAR_CATALOG = {

    "Toyota": [
        "Corolla",
        "Yaris",
        "C-HR"
    ],

    "BMW": [
        "1 Serisi",
        "3 Serisi",
        "5 Serisi"
    ],

    "Mercedes": [
        "A Serisi",
        "C Serisi",
        "E Serisi"
    ],

    "Volkswagen": [
        "Golf",
        "Passat",
        "Polo"
    ],

    "Honda": [
        "Civic",
        "City"
    ],

    "Audi": [
        "A3",
        "A4"
    ],

    "Renault": [
        "Clio",
        "Megane",
        "Talisman"
    ],

}


def parse_vehicle_query(message: str):

    message_lower = message.lower()

    result = {
        "brand": None,
        "model_name": None,
        "year": None
    }


    # Yıl yakala
    year_match = re.search(
        r"\b(19|20)\d{2}\b",
        message
    )

    if year_match:
        result["year"] = int(
            year_match.group()
        )


    # Marka ve model yakala
    for brand, models in CAR_CATALOG.items():

        if brand.lower() in message_lower:

            result["brand"] = brand


            for model in models:

                if model.lower() in message_lower:

                    result["model_name"] = model
                    break


            break


    return result