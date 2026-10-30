from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import Listing
from .serializers import ListingSerializer


class ListingViewSet(viewsets.ModelViewSet):
    """
    /api/listings/                     → sayfalı liste
    /api/listings/?brand=Toyota        → filtre
    /api/listings/?search=corolla      → arama
    /api/listings/?ordering=price      → sıralama
    """
    queryset = Listing.objects.all().order_by("-created_at")
    serializer_class = ListingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["brand", "model_name", "year", "fuel_type", "transmission", "city"]
    search_fields = ["brand", "model_name", "description"]
    ordering_fields = ["price", "year", "mileage_km", "created_at"]
