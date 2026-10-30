from datetime import date

from django import forms

from .catalog import ALL_MODELS, BRANDS
from .models import Listing


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ["brand", "model_name", "year", "mileage_km", "price",
                  "fuel_type", "transmission", "city", "description"]
        labels = {
            "brand": "Marka",
            "model_name": "Model",
            "year": "Model yılı",
            "mileage_km": "Kilometre",
            "price": "Fiyat (TL)",
            "fuel_type": "Yakıt",
            "transmission": "Vites",
            "city": "Şehir",
            "description": "Açıklama",
        }
        widgets = {
            "brand": forms.TextInput(attrs={"list": "brand-options", "autocomplete": "off"}),
            "model_name": forms.TextInput(attrs={"list": "model-options", "autocomplete": "off"}),
            "year": forms.NumberInput(attrs={"min": 1980}),
            "mileage_km": forms.NumberInput(attrs={"min": 0, "step": 1000}),
            "price": forms.NumberInput(attrs={"min": 0, "step": 1000}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Aracın durumu, bakım geçmişi, ekstralar..."}),
        }

    brand_options = BRANDS
    model_options = ALL_MODELS

    def clean_year(self):
        year = self.cleaned_data["year"]
        if year > date.today().year + 1:
            raise forms.ValidationError("Model yılı gelecekte olamaz.")
        return year

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price <= 0:
            raise forms.ValidationError("Fiyat sıfırdan büyük olmalı.")
        return price


class AgentQuestionForm(forms.Form):
    question = forms.CharField(
        label="Sorun",
        max_length=500,
        widget=forms.TextInput(attrs={
            "placeholder": "Örn: 2020 model BMW 3 Serisi kaç TL?",
            "autocomplete": "off",
        }),
    )
