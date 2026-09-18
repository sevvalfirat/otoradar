from django import forms
from .models import Listing

class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ["brand", "model_name", "year", "mileage_km", "price",
                  "fuel_type", "transmission", "city", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }
class AgentQuestionForm(forms.Form):
    question = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Örn: 2019 model dizel Corolla'lar ortalama kaç TL?",
        }),
    )