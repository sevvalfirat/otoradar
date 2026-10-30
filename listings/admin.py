from django.contrib import admin

from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "brand", "model_name", "year", "mileage_km", "price", "fuel_type", "city", "created_at")
    list_filter = ("brand", "fuel_type", "transmission", "city")
    search_fields = ("brand", "model_name", "description")
    ordering = ("-created_at",)
    list_per_page = 50
